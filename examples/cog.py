from discord.commands import Option, slash_command
from discord.ext import commands
from utils.permissions.checks import mod_and_up, whisper
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.slash_perms  import slash_perms

"""
Make sure to add the cog to the initial_extensions list
in main.py
"""

class CogName(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @whisper()
    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Make bot say something", permissions=slash_perms.mod_and_up())
    async def say(self, ctx: BlooContext, *, message: Option(str, description="Message to send")):
        await ctx.respond(message, ephemeral=ctx.whisper)


def setup(bot):
    bot.add_cog(CogName(bot))
