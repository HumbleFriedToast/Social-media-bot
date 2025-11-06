import discord 
import os
from dotenv import load_dotenv
load_dotenv()

print("lancement du bot...")
bot = discord.Client(intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("bot allume !")
@bot.event
async def on_message(message:discord.Message):
    if message.content.lower() =='bonjour' :
        channel= message.channel
        await channel.send("Comment tu vas?")

bot.run(os.getenv('DISCORD_TOKEN'))

