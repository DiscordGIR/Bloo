import discord
from discord.commands import Option, slash_command
from discord.commands.errors import ApplicationCommandInvokeError
from discord.ext import commands
import traceback
from io import BytesIO
from data.model.tag import Tag
from data.services.guild_service import guild_service
from utils.autocompleters.tags import tags_autocomplete
from utils.config import cfg
from utils.context import BlooContext, PromptData
from utils.permissions.checks import (PermissionsFailure, genius_or_submod_and_up)
from utils.permissions.slash_perms import slash_perms

class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_ids=[cfg.guild_id], description="Make bot say something")
    async def tag(self, ctx: BlooContext, name: Option(str, description="Tag name", autocomplete=tags_autocomplete)):
        name = name.lower()
        tag = guild_service.get_tag(name)

        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        # run cooldown so tag can't be spammed
        # bucket = self.tag_cooldown.get_bucket(tag.name)
        # current = ctx.message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
        # # ratelimit only if the invoker is not a moderator
        # if bucket.update_rate_limit(current) and not (ctx.permissions.hasAtLeast(ctx.guild, ctx.author, 5) or ctx.guild.get_role(ctx.settings.guild().role_sub_mod) in ctx.author.roles):
        #     raise commands.BadArgument("That tag is on cooldown.")

        # if the Tag has an image, add it to the embed
        file = tag.image.read()
        if file is not None:
            file = discord.File(BytesIO(
                file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")

        await ctx.respond(embed=await self.prepare_tag_embed(tag), file=file)

    @genius_or_submod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Add a new tag", permissions=slash_perms.genius_or_submod_and_up())
    async def addtag(self, ctx: BlooContext, name: str) -> None:
        """Add a tag. Optionally attach an iamge. (Genius only)

        Example usage
        -------------
        !addtag roblox This is the content

        Parameters
        ----------
        name : str
            "Name of the tag"
        content : str
            "Content of the tag"
        """

        if not name.isalnum():
            raise commands.BadArgument("Tag name must be alphanumeric.")

        if len(name.split()) > 1:
            raise commands.BadArgument("Tag names can't be longer than 1 word.")

        if (guild_service.get_tag(name.lower())) is not None:
            raise commands.BadArgument("Tag with that name already exists.")

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter the content of this tag, and optionally attach an image.",
            convertor=str,
            raw=True)
        description, response = await ctx.prompt(prompt)

        # prepare tag data for database
        tag = Tag()
        tag.name = name.lower()
        tag.content = description
        tag.added_by_id = ctx.author.id
        tag.added_by_tag = str(ctx.author)
        
        # did the user want to attach an image to this tag?
        if len(response.attachments) > 0:
            # ensure the attached file is an image
            image = response.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")
            else:
                image = await image.read()
            # save image bytes
            tag.image.put(image, content_type=_type)

        # store tag in database
        guild_service.add_tag(tag)
        
        _file = tag.image.read()
        if _file is not None:
            _file = discord.File(BytesIO(_file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")

        await ctx.respond(f"Added new tag!", file=_file or discord.MISSING, embed=await self.prepare_tag_embed(tag))

    @genius_or_submod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Delete a tag", permissions=slash_perms.genius_or_submod_and_up())
    async def deltag(self, ctx: BlooContext, name: Option(str, description="Name of tag to delete", autocomplete=tags_autocomplete)):
        """Delete tag (geniuses only)

        Example usage
        --------------
        !deltag <tagname>

        Parameters
        ----------
        name : str
            "Name of tag to delete"

        """

        name = name.lower()

        tag = guild_service.get_tag(name)
        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        guild_service.remove_tag(name)
        await ctx.send_warning(f"Deleted tag {tag.name}.")

    async def prepare_tag_embed(self, tag):
        """Given a tag object, prepare the appropriate embed for it

        Parameters
        ----------
        tag : Tag
            Tag object from database

        Returns
        -------
        discord.Embed
            The embed we want to send
        """
        embed = discord.Embed(title=tag.name)
        embed.description = tag.content
        embed.timestamp = tag.added_date
        embed.color = discord.Color.blue()

        if tag.image.read() is not None:
            embed.set_image(url="attachment://image.gif" if tag.image.content_type ==
                            "image/gif" else "attachment://image.png")
        embed.set_footer(
            text=f"Added by {tag.added_by_tag} | Used {tag.use_count} times")
        return embed

    # @edittag.error
    @tag.error
    # @taglist.error
    @deltag.error
    @addtag.error
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
    bot.add_cog(Tags(bot))
