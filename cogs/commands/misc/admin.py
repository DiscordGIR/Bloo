import discord
from discord.commands import slash_command
from discord.ext import commands

import traceback
from utils.context import BlooContext, PromptData
from utils.logger import logger
from utils.permissions.checks import PermissionsFailure, admin_and_up
from utils.permissions.slash_perms import slash_perms
from utils.config import cfg

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Change bot's profile picture", permissions=slash_perms.mod_and_up())
    async def setpfp(self, ctx: BlooContext, image: discord.Option(discord.Attachment, description="Image to usea as profile picture")):
        """Set the bot's profile picture (admin only)
        
        Example usage
        ------------
        /setpfp
        
        """
        
        if image is None or image.content_type not in ["image/png", "image/jpeg", "image/webp"]:
            raise commands.BadArgument(
                "Please attach an image to use as the profile picture.")

        await self.bot.user.edit(avatar=await image.read())
        await ctx.send_success("Done!", delete_after=5)

    @setpfp.error
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
            logger.error(traceback.format_exc())

def setup(bot):
    bot.add_cog(Admin(bot))
