from discord.ext import commands
import traceback
from utils.context import BlooContext
from utils.permissions.checks import PermissionsFailure

class ErrorHandler(commands.Cog):
    """A cog for global error handling."""

    def __init__(self, bot):
        self.bot = bot

    async def on_command_error(self, ctx: BlooContext, error):
        """A global error handler cog."""
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

def setup(bot: commands.Bot):
    bot.add_cog(ErrorHandler(bot))