import re
import json
from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.messagebus.client import ws
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import LOG

__author__ = 'RReivax'

# This classs listens the log websocket and parses events to save skill related logs.
# Once a skill is started and recognized as a habit, it will call the automation handler. 
class ListenerSkill(MycroftSkill):

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        super(ListenerSkill, self).__init__(name="ListenerSkill")
        self.ws = ws.WebsocketClient()

        self.type_filter = ['mycroft.skill.handler.start',
                            'speak']

    def initialize(self):
        """
        Initiliaze intent and start listening logs.
        """
        LOG.info('INITIALIZE')
        self.load_data_files(dirname(__file__))

        listener_intenet = IntentBuilder("ListenerIntent").\
            require("ListenerKeyword").build()
        self.register_intent(listener_intenet,
                             self.handle_listener_intent)

        self.ws.on('message', self.handle_message)
        self.ws.run_forever()

    def handle_message(self, message):
        """
        This method is called each time a log message is received. It parses
        it and filters to get only skill usage related messages, and write
        them into the logs.json file
        """
        log = json.JSONDecoder().decode(message)

        # regex pattern corresponds to internal skill functions (skill_id:function)
        if log['type'] in self.type_filter or re.match('[0-9]*:.*', log['type']) != None:
            LOG.info('Listener : ' + message)
            with open("/opt/mycroft/habits/logs.json", "a") as f:
                f.write(message + '\n')
        else:
            LOG.info('Listener pass : ' + message)

    def handle_listener_intent(self, message):
        """ Intent response to confirm that this skill is running """
        self.speak_dialog("confirm")

    # The "stop" method defines what Mycroft does when told to stop during
    # the skill's execution.
    def stop(self):
        self.ws.close()

# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return ListenerSkill()
