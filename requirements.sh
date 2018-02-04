#This file is for any packages you need installed for your skill to run
if [ ! -d "~/.mycroft/skills/ListenerSkill/habits" ]; then
   mkdir -p ~/.mycroft/skills/ListenerSkill/habits
   touch ~/.mycroft/skills/ListenerSkill/habits/logs.json
   echo '[]' > ~/.mycroft/skills/ListenerSkill/habits/habits.json
   echo '[]' > ~/.mycroft/skills/ListenerSkill/habits/triggers.json
#   sudo chmod -R ugo+rw /opt/mycroft/habits
fi