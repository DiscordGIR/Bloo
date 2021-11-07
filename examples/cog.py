import traceback

import discord
from discord.commands import Option, slash_command
from discord.ext import commands
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.checks import PermissionsFailure, mod_and_up, whisper
from utils.permissions.slash_perms import slash_perms

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

    @say.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, discord.ApplicationCommandInvokeError):
            error = error.original

        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error("A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(CogName(bot))
