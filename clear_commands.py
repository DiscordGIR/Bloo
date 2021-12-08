import discord
from discord.ext import commands

from dotenv import load_dotenv
import os
import sys
from utils.logger import logger

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.presences = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=False)

bot = commands.Bot(intents=intents, allowed_mentions=mentions)
load_dotenv()

@bot.event
async def on_ready():
    logger.info("""
            88          88                          
            88          88                          
            88          88                          
            88,dPPYba,  88  ,adPPYba,   ,adPPYba,   
            88P'    "8a 88 a8"     "8a a8"     "8a  
            88       d8 88 8b       d8 8b       d8  
            88b,   ,a8" 88 "8a,   ,a8" "8a,   ,a8"  
            8Y"Ybbd8"'  88  `"YbbdP"'   `"YbbdP"'   
                """)
    logger.info(f'Commands have been cleared! Goodbye!')
    os._exit(0)

bot.run(os.environ.get("BLOO_TOKEN"), reconnect=True)
