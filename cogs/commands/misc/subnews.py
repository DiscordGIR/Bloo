import discord
from discord.commands import slash_command
from discord.ext import commands

import traceback
from data.services.guild_service import guild_service
from utils.config import cfg
from utils.logger import logger
from utils.context import BlooContext, PromptData
from utils.permissions.checks import PermissionsFailure, submod_or_admin_and_up
from utils.permissions.slash_perms import slash_perms
from utils.views.prompt import GenericDescriptionModal

class SubNews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @submod_or_admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Post a new subreddit news post", permissions=slash_perms.submod_or_admin_and_up())
    async def subnews(self, ctx: BlooContext, image: discord.Option(discord.Attachment, required=False, description="Image to show in embed")):
        """Posts a new subreddit news post
        
        Example usage
        -------------
        /subnews
        
        """
        db_guild = guild_service.get_guild()

        channel = ctx.guild.get_channel(db_guild.channel_subnews)
        if not channel:
            raise commands.BadArgument("A subreddit news channel was not found. Contact Slim.")

        subnews = ctx.guild.get_role(db_guild.role_sub_news)
        if not subnews:
            raise commands.BadArgument("A subbredit news role was not found. Conact Slim")

        modal = GenericDescriptionModal(author=ctx.author, title=f"New sub news post")
        await ctx.interaction.response.send_modal(modal)
        await modal.wait()

        description = modal.value
        if not description:
            await ctx.send_warning("Cancelled adding meme.")
            return

        body = f"{subnews.mention} New Subreddit news post!\n\n{description}"

        if image is not None:
            # ensure the attached file is an image
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")

            f = await image.to_file()
        else:
            f = None

        await channel.send(content=body, file=f)
        await ctx.send_success("Posted subreddit news post!", delete_after=5, followup=True)

    @subnews.error
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
    bot.add_cog(SubNews(bot))
