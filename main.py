import asyncio
import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    description="Computational Physics Engineering Bot",
)

# Rotating status
STATUSES = [
    discord.Activity(type=discord.ActivityType.playing, name="⚛️ A estudar plasmas"),
    discord.Activity(
        type=discord.ActivityType.watching, name="📖 /help para ver os comandos"
    ),
    discord.Activity(
        type=discord.ActivityType.competing, name="🧮 Engenharia Física e Computacional"
    ),
    discord.Activity(type=discord.ActivityType.listening, name="🎓 Estudem Cálculo!"),
]


@tasks.loop(minutes=5)
async def rotate_status():
    status = STATUSES[rotate_status.current_loop % len(STATUSES)]
    await bot.change_presence(activity=status)


@rotate_status.before_loop
async def before_rotate():
    await bot.wait_until_ready()  # don't start until the bot is connected


# Load cogs
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"  Loaded cog: {filename[:-3]}")
            except Exception as e:
                print(f"  Failed to load {filename[:-3]}: {e}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Connected to {len(bot.guilds)} server(s)")

    # Start rotating status
    if not rotate_status.is_running():
        rotate_status.start()

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# Run
async def main():
    async with bot:
        await load_cogs()
        await bot.start(os.getenv("DISCORD_TOKEN"))


asyncio.run(main())
