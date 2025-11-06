"""
Facebook Discord Bot - Main Entry Point
Loads the Facebook cog and starts the bot
"""

import discord
from discord.ext import commands
import asyncio
import config


# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """Called when bot is ready"""
    print('\n' + '='*60)
    print(f'✅ Bot logged in as: {bot.user.name} (ID: {bot.user.id})')
    print('='*60)
    
    # Load Facebook cog
    try:
        await bot.load_extension('cogs.facebook')
        print('✅ Facebook cog loaded successfully')
    except Exception as e:
        print(f'❌ Failed to load Facebook cog: {e}')
        import traceback
        traceback.print_exc()
    
    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
        print('\n Available Commands:')
        for cmd in synced:
            print(f'  /{cmd.name} - {cmd.description}')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
    
    print('\n' + '='*60)
    print(' Bot is ready! Use commands in Discord.')
    print('='*60 + '\n')


@bot.event
async def on_guild_join(guild):
    """Called when bot joins a server"""
    print(f'✅ Bot joined server: {guild.name} (ID: {guild.id})')


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    print(f'❌ Command error: {error}')


@bot.event
async def on_error(event, *args, **kwargs):
    """Handle general errors"""
    import traceback
    print(f'❌ Error in {event}:')
    traceback.print_exc()


if __name__ == '__main__':
    try:
        print('\n🤖 Starting Facebook Discord Bot...\n')
        bot.run(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        print('\n\n Bot stopped by user')
    except Exception as e:
        print(f'\n❌ Fatal error: {e}')
        import traceback
        traceback.print_exc()
