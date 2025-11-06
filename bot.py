import os
import discord
from discord.ext import commands
import logging
import asyncio
from dotenv import load_dotenv
import utils.database as db
import sqlite3
import os

DB_PATH = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            instagram_id TEXT,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL UNIQUE,
            instagram_token TEXT NOT NULL,
            username TEXT NOT NULL
        );
    ''')
    conn.close()

if not os.path.exists(DB_PATH):
    init_db()
else:
    init_db() 
    
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

#bach nloggiw
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

#intents?(config?)
intents = discord.Intents.default()
intents.message_content = True  # 
intents.members = True  

class SocialMediaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',  
            intents=intents,
            application_id=None,  #
            description='OUR BOT!!!'
        )
        self.initial_extensions = [
            'cogs.instagram',
            'cogs.linkedin',
            'cogs.tiktok',
            'cogs.accounts'
        ]

    async def setup_hook(self):
        logger.info("Starting bot setup...")
        
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")

        await self.tree.sync()
        logger.info("Slash commands synced with Discord")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="your social media"
            )
        )

    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command!")
            return

        logger.error(f"Command error occurred: {error}")
        await ctx.send(f"An error occurred: {str(error)}")

async def main():
    bot = SocialMediaBot()
    
    try:
        async with bot:
            await bot.start(TOKEN)
    except Exception as e:
        logger.error(f"Error?: {e}")
        raise e

if __name__ == "__main__":
    print("waking up......")
    asyncio.run(main())

