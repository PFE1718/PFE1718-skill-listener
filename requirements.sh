#This file is for any packages you need installed for your skill to run
if [ ! -d "/opt/mycroft/habits" ]; then
   sudo mkdir /opt/mycroft/habits
   touch /opt/mycroft/habits/logs.json
   echo '[]' > /opt/mycroft/habits/habits.json
   echo '[]' > /opt/mycroft/habits/triggers.json
   sudo chmod -R ugo+rw /opt/mycroft/habits
fi