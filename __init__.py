import re
import json
import datetime
from os.path import dirname
import os
import threading

from adapt.intent import IntentBuilder
from mycroft.messagebus.client import ws
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import LOG
from mycroft.skills.core import intent_handler
from mycroft.skills.context import adds_context, removes_context

__author__ = 'RReivax'
SKILLS_DIR = '/opt/mycroft/skills'
SKILLS_FOLDERS = {
    "/opt/mycroft/skills/mycroft-skill-listener": "skill listener",
    "/opt/mycroft/skills/mycroft-habit-miner-skill": "habit miner",
    "/opt/mycroft/skills/mycroft-automation-handler": "automation handler"
}


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

        # Time before inactivity callback is launched
        self.reset_tracking_time = 300

        # Load habits file
        with open('/opt/mycroft/habits/habits.json') as habits_file:
            self.habits = json.load(habits_file)
        with open('/opt/mycroft/habits/triggers.json') as triggers_file:
            self.triggers = json.load(triggers_file)
        skill_dir = os.path.dirname(__file__)
        ignore_filepath = "ignore.json"
        ignore_path = os.path.join(skill_dir, ignore_filepath)
        # Load intents to not log
        with open(ignore_path) as ignore_file:
            self.ignored_intents = json.load(ignore_file)

        # Set up array with habits to detect (first time detection)
        self.habits_to_choose = []
        for habit_index, habit in enumerate(self.habits):
            if habit['user_choice'] is False:
                habit['index'] = habit_index
                for intent in habit['intents']:
                    # Variable to keep track of the intent to detect habits
                    intent['occured'] = False

                self.habits_to_choose.append(habit)

        # Set up callback to reset intent tracking when inactivity is detected.
        # This callback will also launch the habit miner skill.
        self.inactivity_tracking_timer = threading.Timer(
            self.reset_tracking_time, self.inactivity_reset)
        self.inactivity_tracking_timer.start()

        # Starts listening in background.
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

        if (re.match('-?[0-9]*:.*', log['type']) is not None and
                log['type'] not in self.ignored_intents):
            LOG.info('Listener : ' + message)
            LOG.info("Listener - Handle message")

            context = log['context']['target']
            if context is not None:
                return
            # Resets inactivity timer
            self.inactivity_tracking_timer.cancel()
            self.inactivity_tracking_timer = threading.Timer(
                self.reset_tracking_time, self.inactivity_reset)
            self.inactivity_tracking_timer.start()

            # Check if intent is a trigger
            self.check_trigger(log)

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

                if sorted(log_cmp.items()) == sorted(intent_cmp.items()):
                    intent['occured'] = True
                    self.check_habit_completed(habit)
        LOG.info("Listener - Intent checked")

    def check_habit_completed(self, habit):
        """
        Checks if all the intents in a habit have occured.
        """
        habit_occured = True
        for intent in habit['intents']:
            if intent['occured'] is False:
                habit_occured = False
                break

        if habit_occured is True:
            # Check if habit is a frequency habit
            if habit.get('interval_max', None) is not None:
                now = datetime.datetime.now().time()
                habit_time = datetime.datetime(1, 1, 1,
                                               int(habit['time']
                                                   .split(':')[0]),
                                               int(habit['time']
                                                   .split(':')[1]))
                # if datetime.datetime.now().weekday() in habit['days']:
                if (now < (habit_time + datetime.timedelta(
                        minutes=float(habit['interval_max']))).time() and
                    now > (habit_time - datetime.timedelta(
                        minutes=float(habit['interval_max']))).time()):
                    LOG.info("Frequency habit detected")
                else:
                    return

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
        self.wsc.emit(
            Message("recognizer_loop:utterance",
                    {
                        "utterances":
                            ["start habit mining"],
                            "lang": 'en-us'
                    }))
        # Reload habits and triggers to be updated and resets intents occurence
        self.load_files()


class ListenerSkill(MycroftSkill):
    """
    This class launches the listener thread at initialization and handles
    basic intent response to check if the skill is running.
    """

    def __init__(self):
        super(ListenerSkill, self).__init__(name="ListenerSkill")

        self.to_install = []
        if not self.check_skills_intallation():
            return

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

    def check_skills_intallation(self):
        LOG.info("Checking for skills install...")
        ret = True
        for folder, skill in SKILLS_FOLDERS.iteritems():
            if not os.path.isdir(folder):
                ret = False
                self.to_install += [skill]

        if not ret:
            self.set_context("InstallMissingContext")
            dial = "To use this skill, you also have to install the skill"
            num_skill = "this skill"
            skills_list = ""
            for skill in self.to_install[:-1]:
                skills_list += skill + ", "
            if len(self.to_install) > 1:
                num_skill = "these {} skills".format(len(self.to_install))
                skills_list += "and "
                dial += "s"
            skills_list += self.to_install[-1]
            self.speak(dial + " " + skills_list +
                       ". Should I install {} for you?".format(num_skill),
                       expect_response=True)
        return ret

    @intent_handler(IntentBuilder("InstallMissingIntent")
                    .require("YesKeyword")
                    .require("InstallMissingContext").build())
    @removes_context("InstallMissingContext")
    def handle_install_missing(self):
        for skill in self.to_install:
            self.emitter.emit(
                Message("recognizer_loop:utterance",
                        {"utterances": ["install " + skill],
                         "lang": 'en-us'}))

    @intent_handler(IntentBuilder("NotInstallMissingIntent")
                    .require("NoKeyword")
                    .require("InstallMissingContext").build())
    @removes_context("InstallMissingContext")
    def handle_not_install_missing(self):
        pass

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
