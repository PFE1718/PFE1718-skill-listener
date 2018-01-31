# Listener Skill

This skill is made to work with the full Habits Automation project https://github.com/PFE1718/mycroft-skills-automation. 

Its role is to log mycroft intents when the user launches a skill. It runs continuously in the background and calls the other two skills of the project by utterance when necessary.
Different cases : 
 - skill trigger detected (calls the automation handler skill)
 - Frequency habit detected (calls the automation handler skill)
 - habit completed for the first time (calls the automation handler skill)
 - inactivity for more than 5 minutes after last command (calls the data mining skill)

## Current state

Working features:
 - Trigger detection
 - Frequency habit detection
 - Habit completed detection
 - Inactivity detection
 - Automation handler skill and Habit miner skill launching

Known issues:
 - 

TODO:
 