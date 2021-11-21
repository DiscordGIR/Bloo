import discord
from discord.commands import slash_command
from discord.commands.commands import Option
from discord.ext import commands

import datetime
import traceback
from data.services.guild_service import guild_service
from utils.config import cfg
from utils.context import BlooContext, PromptData
from utils.permissions.checks import (PermissionsFailure, genius_or_submod_and_up)
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
            description="Please enter a description of this common issue (optionally attach an image).",
            convertor=str,
            raw=True)

        res = await ctx.prompt(prompt)
        if res is None:
            await ctx.send_warning("Cancelled new common issue.")
            return
        
        description, response = res

        embed, f = await self.prepare_issues_embed(title, description, response)
        await channel.send(embed=embed, file=f)
        await ctx.send_success("Common issue posted!", delete_after=5)
    
    @genius_or_submod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Submit a new common issue", permissions=slash_perms.genius_or_submod_and_up())
    async def postembed(self, ctx: BlooContext, *, title: str):
        """Post an embed in the current channel (Geniuses only)

        Example usage
        ------------
        /postembed This is a title (you will be prompted for a description)

        Parameters
        ----------
        title : str
            "Title for the embed"
        
        """

        # get #common-issues channel
        channel = ctx.channel

        # prompt the user for common issue body
        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter a description of this embed (optionally attach an image)",
            convertor=str,
            raw=True)

        res = await ctx.prompt(prompt)
        if res is None:
            await ctx.send_warning("Cancelled new embed.")
            return

        description, response = res

        embed, f = await self.prepare_issues_embed(title, description, response)
        await channel.send(embed=embed, file=f)

    @genius_or_submod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Submit a new common issue", permissions=slash_perms.genius_or_submod_and_up())
    async def rawembed(self, ctx: BlooContext, *, channel: Option(discord.TextChannel, description="Channel the embed is in"), message_id: Option(str, description="ID of the message with the embed")):
        try:
            message_id = int(message_id)
        except:
            raise commands.BadArgument("Invalid message ID!")
        
        try:
            message: discord.Message = await channel.fetch_message(message_id)
        except Exception:
            raise commands.BadArgument("Could not find a message with that ID!")
        
        if message.author != ctx.me:
            raise commands.BadArgument("I didn't post that embed!")
        
        if len(message.embeds) == 0:
            raise commands.BadArgument("Message does not have an embed!")

        if message.embeds[0].image:
            if len(message.embeds[0].description) + len(message.embeds[0].image.url) > 2000:
                await ctx.respond(f"{message.embeds[0].description[:1990-len(message.embeds[0].image.url)]}...\n\n{message.embeds[0].image.url}",  allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))
            else:
                await ctx.respond(f"{message.embeds[0].description}\n\n{message.embeds[0].image.url}",  allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))
        else:
            await ctx.respond(message.embeds[0].description[:1997] + "..." if len(message.embeds[0].description) > 2000 else "", allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))

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

    @rawembed.error
    @postembed.error
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
