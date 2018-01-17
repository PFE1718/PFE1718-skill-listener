import re
import json
import datetime
from os.path import dirname
import threading

from adapt.intent import IntentBuilder
from mycroft.messagebus.client import ws
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

        with open('/opt/mycroft/habits/habits.json') as habits_file:
            self.habits = json.load(habits_file)
        with open('/opt/mycroft/habits/triggers.json') as triggers_file:
            self.triggers = json.load(triggers_file)

        # Stores the last user actions to check if matching a habit
        self.last_intents = []

        self.daemon = True
        self.start()

    def run(self):
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

            # Check if intent is a trigger
            trigger_id = self.check_trigger(log)
            if trigger_id is not None:
                LOG.info('TRIGGER FOUND ' + trigger_id)

                # Adds datetime field to the event
            log['datetime'] = str(datetime.datetime.now())
            message_time = json.dumps(log)
            with open("/opt/mycroft/habits/logs.json", "a") as log_file:
                log_file.write(message_time + '\n')
        else:
            LOG.info('Listener pass : ' + message)

    def check_trigger(self, log):
        """
        Checks if the intent matches a trigger.
        """
        intent_found = None
        for trigger_id in self.triggers:
            if log['type'] == self.triggers[trigger_id]['intent']:
                intent_found = trigger_id
                # Checks if parameters of the intent match those of the trigger
                for param in self.triggers[trigger_id]['parameters']:
                    if log['data'].get(param) != \
                            self.triggers[trigger_id]['parameters'][param]:
                        return None

        return intent_found


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

        listener_intenet = IntentBuilder("ListenerIntent").\
            require("ListenerKeyword").build()
        self.register_intent(listener_intenet,
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
