import os

import discord
from discord.ext import commands
from discord.interactions import Interaction
from dotenv.main import load_dotenv

from data.model.guild import Guild
from utils.config import cfg
from utils.context import GIRContext
from utils.database import db
from utils.permissions import permissions
from utils.logger import logger

initial_extensions = [
        "cogs.commands.info.stats",
        "cogs.commands.info.devices",
        "cogs.commands.info.userinfo",
        "cogs.commands.info.tags",
    ]
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.presences = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=False)


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # force the config object and database connection to be loaded
        if cfg and db and permissions:
            logger.info("Presetup phase completed! Connecting to Discord...")

    async def get_application_context(self, interaction: Interaction, *, cls=GIRContext) -> GIRContext:
        return await super().get_application_context(interaction, cls=cls)

bot = Bot(intents=intents, allowed_mentions=mentions)

@bot.event
async def on_ready():
    logger.info("""                   
                         _      
                        (_)     
                    __ _ _ _ __ 
                   / _` | | '__|
                  | (_| | | |   
                   \__, |_|_|   
                    __/ |       
                   |___/            
                """)
    logger.info(f'\n\nLogged in as: {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')


if __name__ == '__main__':
    for extension in initial_extensions:
        bot.load_extension(extension)

bot.run(os.environ.get("GIR_TOKEN"), reconnect=True)
