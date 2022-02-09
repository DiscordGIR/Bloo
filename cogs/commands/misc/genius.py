import discord
from discord.commands import slash_command
from discord.commands import Option
from discord.ext import commands

import datetime
import traceback
from data.services.guild_service import guild_service
from utils.autocompleters import issue_autocomplete
from utils.config import cfg
from utils.logger import logger
from utils.context import BlooContext, PromptData
from utils.permissions.checks import (PermissionsFailure, always_whisper, genius_or_submod_and_up, whisper_in_general)
from utils.permissions.slash_perms import slash_perms


class Genius(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = []

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
        await self.do_reindex(channel)

    @genius_or_submod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Post an embed", permissions=slash_perms.genius_or_submod_and_up())
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
    @slash_command(guild_ids=[cfg.guild_id], description="Repost common-issues table of contents", permissions=slash_perms.genius_or_submod_and_up())
    async def reindexissues(self, ctx: BlooContext):
        # get #common-issues channel
        channel: discord.TextChannel = ctx.guild.get_channel(
            guild_service.get_guild().channel_common_issues)
        if not channel:
            raise commands.BadArgument("common issues channel not found")

        await ctx.defer(ephemeral=True)
        res = await self.do_reindex(channel)

        if res is None:
            raise commands.BadArgument("Something unexpected occured")

        count, page = res
        await ctx.send_success(f"Indexed {count} issues and posted {page} Table of Contents embeds!")

    async def do_reindex(self, channel):
        contents = {}
        async for message in channel.history(limit=None, oldest_first=True):
            if message.author.id != self.bot.user.id:
                continue

            if not message.embeds:
                continue

            embed = message.embeds[0]
            if not embed.footer.text:
                continue
            
            if embed.footer.text.startswith("Submitted by"):
                contents[f"{embed.title}"] = message
            elif embed.footer.text.startswith("Table of Contents"):
                await message.delete()
            else:
                continue

        page = 1
        count = 1
        toc_embed = discord.Embed(title="Table of Contents", description="Click on a link to jump to the issue!\n", color=discord.Color.gold())
        toc_embed.set_footer(text=f"Table of Contents • Page {page}")
        for title, message in contents.items():
            this_line = f"\n{count}. [{title}]({message.jump_url})"
            count += 1
            if len(toc_embed.description) + len(this_line) < 4096:
                toc_embed.description += this_line
            else:
                await channel.send(embed=toc_embed)
                page += 1
                toc_embed.description = ""
                toc_embed.title = ""
                toc_embed.set_footer(text=f"Table of Contents • Page {page}")

        self.bot.issue_cache.cache = contents
        await channel.send(embed=toc_embed)
        return count, page

    @genius_or_submod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Post raw body of an embed", permissions=slash_perms.genius_or_submod_and_up())
    async def rawembed(self, ctx: BlooContext, *, channel: Option(discord.TextChannel, description="Channel the embed is in"), message_id: Option(str, description="ID of the message with the embed"), mobile_friendly: Option(bool, description="Whether to display the tag in a mobile friendly format")):
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
        
        _file = message.embeds[0].image
        response = discord.utils.escape_markdown(message.embeds[0].description) if not mobile_friendly else message.embeds[0].description
        parts = [response[i:i+2000] for i in range(0, len(response), 2000)]

        for i, part in enumerate(parts):
            if i == 0:
                await ctx.respond(part, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))
            else:
                await ctx.send(part, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))

        if _file:
            await ctx.send(_file.url, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))

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

    @whisper_in_general()
    @slash_command(guild_ids=[cfg.guild_id], description="Post the embed for one of the common issues")
    async def issue(self, ctx: BlooContext, title: Option(str, autocomplete=issue_autocomplete), user_to_mention: Option(discord.Member, description="User to mention in the response", required=False)):
        if title not in self.bot.issue_cache.cache:
            raise commands.BadArgument("Issue not found! Title must match one of the embeds exactly, use autocomplete to help!")

        message = self.bot.issue_cache.cache[title]
        embed = message.embeds[0]

        if user_to_mention is not None:
            title = f"Hey {user_to_mention.mention}, have a look at this!"
        else:
            title = None

        await ctx.respond_or_edit(content=title, embed=embed, ephemeral=ctx.whisper)

    @issue.error
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
            logger.error(traceback.format_exc())


def setup(bot):
    bot.add_cog(Genius(bot))
