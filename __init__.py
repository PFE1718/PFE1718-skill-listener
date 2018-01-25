import re
import json
import datetime
from os.path import dirname
import threading

from adapt.intent import IntentBuilder
from mycroft.messagebus.client import ws
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import LOG

__author__ = 'RReivax'


class ListenerThread(threading.Thread):
    """
    This classs listens the log websocket and parses events to save skill
    related logs. Once a skill is started and recognized as a trigger, it will
    call the automation handler. Once multiple skills composing a habbit are
    launched, it will also call the automation handler.
    """

    def __init__(self):
        super(ListenerThread, self).__init__()
        self.wsc = ws.WebsocketClient()
        self.wsc.on('message', self.handle_message)

        self.reset_tracking_time = 20

        with open('/opt/mycroft/habits/habits.json') as habits_file:
            self.habits = json.load(habits_file)
        with open('/opt/mycroft/habits/triggers.json') as triggers_file:
            self.triggers = json.load(triggers_file)

        self.habits_to_choose = []
        for habit_index, habit in enumerate(self.habits):
            if habit['user_choice'] is False:
                habit['index'] = habit_index
                for intent in habit['intents']:
                    # Variable to keep track of the intent to detect habits
                    intent['occured'] = False

                self.habits_to_choose.append(habit)

        self.inactivity_tracking_timer = threading.Timer(
            self.reset_tracking_time, self.inactivity_reset)
        self.inactivity_tracking_timer.start()

        self.daemon = True
        self.start()

    def load_files(self):
        """ Reloads json files """
        with open('/opt/mycroft/habits/habits.json') as habits_file:
            self.habits = json.load(habits_file)
        with open('/opt/mycroft/habits/triggers.json') as triggers_file:
            self.triggers = json.load(triggers_file)

        self.habits_to_choose = []
        for habit_index, habit in enumerate(self.habits):
            if habit['user_choice'] is False:
                habit['index'] = habit_index
                for intent in habit['intents']:
                    # Variable to keep track of the intent to detect habits
                    intent['occured'] = False
                self.habits_to_choose.append(habit)

    def run(self):
        """ Runs continuously on a separated thread. Listens to the bus"""
        self.wsc.run_forever()

    def handle_message(self, message):
        """
        This method is called each time a log message is received. It parses
        it and filters to get only skill usage related messages, and write
        them into the logs.json file.
        """

        log = json.JSONDecoder().decode(message)
        # Regex pattern corresponds to internal skill functions/intent handler
        # (skill_id:function)
        if re.match('-?[0-9]*:.*', log['type']) is not None:
            LOG.info('Listener : ' + message)
            LOG.info("Listener - Handle message")
            # Resets inactivity timer
            self.inactivity_tracking_timer.cancel()
            self.inactivity_tracking_timer = threading.Timer(
                self.reset_tracking_time, self.inactivity_reset)
            self.inactivity_tracking_timer.start()

            # Check if intent is a trigger
            trigger_id = self.check_trigger(log)

            # Adds datetime field to the event
            log['datetime'] = str(datetime.datetime.now())
            log['utterance'] = log['data'].get('utterance', 'No voice command')
            # Removes unwanted elements
            log.pop('context', None)
            log['data'].pop('confidence', None)
            log['data'].pop('target', None)
            log['data'].pop('__tags__', None)
            log['data'].pop('utterance', None)
            # Redundant with Type field, so removed
            log['data'].pop('intent_type', None)
            # Moves voice command field outside "data" field to only keep
            # skill parameters in "data"
            # Rename "data" into "parameters"
            log['parameters'] = log.pop('data')

            # Check if intent is part of a habit
            self.check_intent(log)

            message_time = json.dumps(log)
            with open("/opt/mycroft/habits/logs.json", "a") as log_file:
                log_file.write(message_time + '\n')

    def check_trigger(self, log):
        """
        Checks if the intent matches a trigger.
        """
        intent_found = None
        for trigger_id, trigger in enumerate(self.triggers):
            if log['type'] == trigger['intent']:
                intent_found = trigger_id
                # Checks if parameters of the intent match those of the trigger
                for param in trigger['parameters']:
                    if log['data'].get(param) != trigger['parameters'][param]:
                        return None

        if intent_found is not None:
            LOG.info("Trigger detected number " + str(intent_found))
            # Call the automation handler by utterance
            self.wsc.emit(
                Message("recognizer_loop:utterance",
                        {
                            "utterances":
                            ["trigger detected number " + str(intent_found)],
                            "lang": 'en-us'
                        }))

        return intent_found

    def check_intent(self, log):
        """
        Checks if an intent is part of an habit. If so, tags the intent and
        calls check_habit_complted for the concerned habits.
        """
        LOG.info("Listener - Checking Intent..." +
                 str(len(self.habits_to_choose)))
        log_cmp = dict()
        intent_cmp = dict()

        # Tags intent as 'occured' in habits
        for habit in self.habits_to_choose:
            for intent in habit['intents']:
                log_cmp['name'] = log['type']
                log_cmp['parameters'] = log['parameters']
                intent_cmp['name'] = intent['name']
                intent_cmp['parameters'] = intent['parameters']

                LOG.info(log_cmp)
                LOG.info(intent_cmp)

                if sorted(log_cmp.items()) == sorted(intent_cmp.items()):
                    LOG.info('Intent occured')
                    intent['occured'] = True
                    self.check_habit_completed(habit)
        LOG.info("Listener - Intent checked")

    def check_habit_completed(self, habit):
        """
        Checks if all the intents in a habit have occured.
        """
        LOG.info("Checking this : " + str(habit))
        habit_occured = True
        for intent in habit['intents']:
            if intent['occured'] is False:
                habit_occured = False
                break

        if habit_occured is True:
            LOG.info('Habit detected number ' + str(habit['index']))
            # Call the automation handler by utterance
            self.wsc.emit(
                Message("recognizer_loop:utterance",
                        {
                            "utterances":
                            ["habit detected number " + str(habit['index'])],
                            "lang": 'en-us'
                        }))

    def inactivity_reset(self):
        """
        Resets currently occured intents as they should no longer be part of a
        habit.
        """
        LOG.info("Listener - Inactivity")
        # Reload habits and triggers to be updated and resets intents occurence
        self.load_files()


class ListenerSkill(MycroftSkill):
    """
    This class launches the listener thread at initialization and handles
    basic intent response to check if the skill is running.
    """

    def __init__(self):
        super(ListenerSkill, self).__init__(name="ListenerSkill")
        ListenerThread()

    def initialize(self):
        """
        Initiliaze intent and start listening logs.
        """
        LOG.info('INITIALIZE Listener')
        self.load_data_files(dirname(__file__))

        listener_intent = IntentBuilder("ListenerIntent").\
            require("ListenerKeyword").build()
        self.register_intent(listener_intent,
                             self.handle_listener_intent)

    def handle_listener_intent(self, message):
        """ Intent response to confirm that this skill is running. """
        self.speak_dialog("confirm")

    def stop(self):
        """
        The "stop" method defines what Mycroft does when told to stop during
        the skill's execution.
        """
        pass


def create_skill():
    """
    The "create_skill()" method is used to create an instance of the skill.
    """
    return ListenerSkill()
