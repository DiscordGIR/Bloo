import traceback

from data.services.guild_service import guild_service
from discord.commands.commands import slash_command
from discord.commands.errors import ApplicationCommandInvokeError
from discord.ext import commands
from utils.config import cfg
from utils.context import BlooContext, PromptData
from utils.permissions.checks import PermissionsFailure, submod_or_admin_and_up
from utils.permissions.slash_perms import slash_perms


class SubNews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @submod_or_admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Post a new subreddit news post", permissions=slash_perms.submod_or_admin_and_up())
    async def subnews(self, ctx: BlooContext):
        if not ctx.guild.id == cfg.guild_id:
            return

        db = guild_service.get_guild()
        
        channel = ctx.guild.get_channel(db.channel_subnews)
        if not channel:
            raise commands.BadArgument("A subreddit news channel was not found. Contact Slim.")

        subnews = ctx.guild.get_role(db.role_sub_news)
        if not subnews:
            raise commands.BadArgument("A subbredit news role was not found. Conact Slim")
        
        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter a description of this common issue.",
            convertor=str,
            raw=True)
        description, response = await ctx.prompt(prompt)
        if description is None:
            await ctx.send_warning("Cancelled subnews post.")
            return

        body = f"{subnews.mention} New Subreddit news post!\n\n{description}"

        if len(response.attachments) > 0:
            # ensure the attached file is an image
            image = response.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")

            f = await image.to_file()
        else:
            f = None

        await channel.send(content=body, file=f)
        await ctx.send_success("Posted subreddit news post!")

    @subnews.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, ApplicationCommandInvokeError):
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
    bot.add_cog(SubNews(bot))
