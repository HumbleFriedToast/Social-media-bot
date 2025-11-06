"""
Social Media Discord Bot - Main Entry Point
Loads all cogs (Facebook, Instagram, LinkedIn, TikTok, Accounts)
and starts the bot.
"""

import discord
from discord.ext import commands
import asyncio
import traceback
import config

# -------------------------------------------------------------
# Bot setup
# -------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# List of all cogs to load
COGS = [
    "cogs.instagram",
    "cogs.facebook"
]


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    print('\n' + '=' * 70)
    print(f'Bot logged in as: {bot.user.name} (ID: {bot.user.id})')
    print('=' * 70)
    print('\nLoading extensions...')

    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f'Loaded cog: {cog}')
        except Exception as e:
            print(f' Failed to load cog {cog}: {e}')
            traceback.print_exc()

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'\n Synced {len(synced)} slash commands\n')
        print("📜 Available Commands:")
        for cmd in synced:
            print(f'  /{cmd.name} - {cmd.description}')
    except Exception as e:
        print(f' Failed to sync commands: {e}')

    print('\n' + '=' * 70)
    print('Bot is ready! Use commands in Discord.')
    print('=' * 70 + '\n')


@bot.event
async def on_guild_join(guild):
    """Called when the bot joins a server."""
    print(f'Bot joined server: {guild.name} (ID: {guild.id})')


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        return
    print(f' Command error: {error}')


@bot.event
async def on_error(event, *args, **kwargs):
    """Handle unexpected errors."""
    print(f'❌ Error in {event}:')
    traceback.print_exc()


# -------------------------------------------------------------
# Optional: Fallback default values for config
# -------------------------------------------------------------
if not hasattr(config, "INSTAGRAM_MAX_CALLS"):
    config.INSTAGRAM_MAX_CALLS = 100  # safe default

if not hasattr(config, "INSTAGRAM_TIME_WINDOW"):
    config.INSTAGRAM_TIME_WINDOW = 60  # seconds

if not hasattr(config, "DISCORD_TOKEN"):
    raise ValueError("Missing DISCORD_TOKEN in config.py")


# -------------------------------------------------------------
# Add Instagram callback fix to PostScheduler
# -------------------------------------------------------------
try:
    from cogs.facebook import PostScheduler
    if not hasattr(PostScheduler, "set_instagram_callback"):
        def set_instagram_callback(self, callback):
            self.instagram_callback = callback

        setattr(PostScheduler, "set_instagram_callback", set_instagram_callback)
        print("Added missing set_instagram_callback() method to PostScheduler")
except Exception as e:
    print(f" Could not patch PostScheduler: {e}")


# -------------------------------------------------------------
# Run the bot
# -------------------------------------------------------------
if __name__ == "__main__":
    try:
        print("\nStarting Social Media Discord Bot...\n")
        bot.run(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"\n Fatal error: {e}")
        traceback.print_exc()
