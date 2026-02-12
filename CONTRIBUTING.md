# Contributing

Thanks for wanting to contribute! 
This document should help you understand how to do it, in case you have any questions don't hesitate to send a message to this discord: igp18

## How to Get Started

### 1. Create your own test bot

Don't use the production bot token for development. Create your own:

1. Go to https://discord.com/developers/applications
2. Create a new application
3. Add a bot, copy the token
4. Create a test Discord server and invite your bot there

### 2. Set up the project
```bash
git clone https://github.com/igp183/lefc_bot.git
cd lefc_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and paste your test bot token
python main.py
```

### 3. Create a new feature

All features are organized as **cogs** (self-contained modules).
To add a feature:

1. Create a new file in `cogs/`, e.g. `cogs/my_feature.py`
2. Use this template:
```python
import discord
from discord.ext import commands
from discord import app_commands

class MyFeature(commands.Cog):
    """Short description of what this does."""
    emoji = "🏷️" # optional, used for the help command

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="mycommand", description="What it does")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!")

async def setup(bot: commands.Bot):
    await bot.add_cog(MyFeature(bot))
```

3. That's it, `main.py` auto-loads all cogs from the folder.

### 4. Submit a Pull Request

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Push and open a PR

## Guidelines

- One cog per feature (single responsiblity)
- Use slash commands (`@app_commands.command`) over prefix commands
- Test locally with your own bot before submitting