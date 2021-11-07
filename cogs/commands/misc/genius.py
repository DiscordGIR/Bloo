import datetime
import traceback

import discord
from data.services.guild_service import guild_service
from discord.commands import slash_command
from discord.ext import commands
from utils.config import cfg
from utils.context import BlooContext, PromptData
from utils.permissions.checks import (PermissionsFailure,
                                      genius_or_submod_and_up)
from utils.permissions.slash_perms import slash_perms


class Genius(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @genius_or_submod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Submit a new common issue", permissions=slash_perms.genius_or_submod_and_up())
    async def commonissue(self, ctx: BlooContext, *, title: str):
        """Submit a new common issue (Geniuses only)
        Example usage
        ------------
        /commonissue This is a title (you will be prompted for a description)
        Parameters
        ----------
        title : str
            "Title for the issue"
        """

        # get #common-issues channel
        channel = ctx.guild.get_channel(
            guild_service.get_guild().channel_common_issues)
        if not channel:
            raise commands.BadArgument("common issues channel not found")

        # prompt the user for common issue body
        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter a description of this common issue.",
            convertor=str,
            raw=True)

        description, response = await ctx.prompt(prompt)
        if description is None:
            await ctx.send_warning("Cancelled new common issue.")
            return

        embed, f = await self.prepare_issues_embed(title, description, response)
        await channel.send(embed=embed, file=f)
        await ctx.send_success("Common issue posted!")

    async def prepare_issues_embed(self, title, description, message):
        embed = discord.Embed(title=title)
        embed.color = discord.Color.random()
        embed.description = description
        f = None

        # did the user want to attach an image to this tag?
        if len(message.attachments) > 0:
            # ensure the attached file is an image
            image = message.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")

            f = await image.to_file()
            embed.set_image(url=f"attachment://{f.filename}")

        embed.set_footer(text=f"Submitted by {message.author}")
        embed.timestamp = datetime.datetime.now()
        return embed, f

    @commonissue.error
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
    bot.add_cog(Genius(bot))
