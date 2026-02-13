# ~/lefc_bot/deploy.sh
#!/bin/bash
cd ~/lefc_bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart discordbot
echo "Bot updated and restarted."