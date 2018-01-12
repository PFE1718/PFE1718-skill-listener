# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


# Visit https://docs.mycroft.ai/skill.creation for more detailed information
# on the structure of this skill and its containing folder, as well as
# instructions for designing your own skill based on this template.


# Import statements: the list of outside modules you'll be using in your
# skills, whether from other files in mycroft-core or from external libraries
from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import LOG
from mycroft.messagebus.client import ws

__author__ = 'RReivax'
 
# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.

# The logic of each skill is contained within its own class, which inherits
# base methods from the MycroftSkill class with the syntax you can see below:
# "class ____Skill(MycroftSkill)"
class ListenerSkill(MycroftSkill):

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        super(ListenerSkill, self).__init__(name="ListenerSkill")
        self.ws = ws.WebsocketClient()

    # This method loads the files needed for the skill's functioning, and
    # creates and registers each intent that the skill uses
    def initialize(self):
        LOG.info('INITIALIZE')
        self.load_data_files(dirname(__file__))

        listener_intenet = IntentBuilder("ListenerIntent").\
            require("ListenerKeyword").build()
        self.register_intent(listener_intenet, 
                            self.handle_listener_intenet)

        def echo(message):
            LOG.info('Listener : ' + message)


        self.ws.on('message', echo)
        self.ws.run_forever()

    def handle_listener_intenet(self, message):
        self.speak_dialog("confirm")


    # The "stop" method defines what Mycroft does when told to stop during
    # the skill's execution.
    def stop(self):
        self.ws.close()

# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return ListenerSkill()
