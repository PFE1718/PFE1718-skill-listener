#This file is for any packages you need installed for your skill to run
if [ ! -d "/opt/mycroft/skills/PFE1718-skill-listener/habits" ]; then
   mkdir /opt/mycroft/skills/PFE1718-skill-listener/habits
   touch /opt/mycroft/skills/PFE1718-skill-listener/logs.json
   echo '[]' > /opt/mycroft/skills/PFE1718-skill-listener/habits/habits.json
   echo '[]' > /opt/mycroft/skills/PFE1718-skill-listener/habits/triggers.json
#   sudo chmod -R ugo+rw /opt/mycroft/habits
fi