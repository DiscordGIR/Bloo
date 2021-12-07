import discord
from discord.commands import Option, slash_command
from discord.ext import commands
from discord.ext.commands.cooldowns import CooldownMapping

import traceback
from datetime import datetime
from io import BytesIO
from data.model.tag import Tag
from utils.message_cooldown import MessageTextBucket
from data.services.guild_service import guild_service
from utils.autocompleters import memes_autocomplete
from utils.config import cfg
from utils.logger import logger
from utils.context import BlooContext, PromptData
from utils.permissions.checks import (PermissionsFailure,
                                      mod_and_up, whisper)
from utils.permissions.slash_perms import slash_perms
from utils.permissions.permissions import permissions
from utils.menu import Menu

async def format_meme_page(entries, all_pages, current_page, ctx):
        embed = discord.Embed(
            title=f'All memes', color=discord.Color.blurple())
        for meme in entries:
            desc = f"Added by: {meme.added_by_tag}\nUsed {meme.use_count} times"
            if meme.image.read() is not None:
                desc += "\nHas image attachment"
            embed.add_field(name=meme.name, value=desc)
        embed.set_footer(
            text=f"Page {current_page} of {len(all_pages)}")
        return embed

class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meme_cooldown = CooldownMapping.from_cooldown(1, 5, MessageTextBucket.custom)

    @slash_command(guild_ids=[cfg.guild_id], description="Display a meme")
    async def meme(self, ctx: BlooContext, name: Option(str, description="Meme name", autocomplete=memes_autocomplete), user_to_mention: Option(discord.Member, description="User to mention in the response", required=False)):
        """Displays a meme.
        
        Example usage
        -------------
        /meme name:<memename>
        
        Parameters
        ----------
        name : str
            "Name of meme to display"
        
        """
        name = name.lower()
        meme = guild_service.get_meme(name)

        if meme is None:
            raise commands.BadArgument("That meme does not exist.")

        # run cooldown so meme can't be spammed
        bucket = self.meme_cooldown.get_bucket(meme.name)
        current = datetime.now().timestamp()
        # ratelimit only if the invoker is not a moderator
        if bucket.update_rate_limit(current) and not (permissions.has(ctx.guild, ctx.author, 5) or ctx.guild.get_role(guild_service.get_guild().role_sub_mod) in ctx.author.roles):
            raise commands.BadArgument("That meme is on cooldown.")

        # if the Meme has an image, add it to the embed
        file = meme.image.read()
        if file is not None:
            file = discord.File(BytesIO(
                file), filename="image.gif" if meme.image.content_type == "image/gif" else "image.png")

        if user_to_mention is not None:
            title = user_to_mention.mention
        else:
            title = None

        await ctx.respond(content=title, embed=await self.prepare_meme_embed(meme), file=file)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Add a new meme", permissions=slash_perms.mod_and_up())
    async def addmeme(self, ctx: BlooContext, name: str) -> None:
        """Add a meme. Optionally attach an image. (Genius only)

        Example usage
        -------------
        /addmeme roblox

        Parameters
        ----------
        name : str
            "Name of the meme"
        
        """

        if not name.isalnum():
            raise commands.BadArgument("Meme name must be alphanumeric.")

        if len(name.split()) > 1:
            raise commands.BadArgument(
                "Meme names can't be longer than 1 word.")

        if (guild_service.get_meme(name.lower())) is not None:
            raise commands.BadArgument("Meme with that name already exists.")

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter the content of this meme, and optionally attach an image.",
            convertor=str,
            raw=True)
        res = await ctx.prompt(prompt)

        if res is None:
            await ctx.send_warning("Cancelled.")
            return
            
        description, response = res
        # prepare meme data for database
        meme = Tag()
        meme.name = name.lower()
        meme.content = description
        meme.added_by_id = ctx.author.id
        meme.added_by_tag = str(ctx.author)

        # did the user want to attach an image to this meme?
        if len(response.attachments) > 0:
            # ensure the attached file is an image
            image = response.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")
            else:
                image = await image.read()
            # save image bytes
            meme.image.put(image, content_type=_type)

        # store meme in database
        guild_service.add_meme(meme)

        _file = meme.image.read()
        if _file is not None:
            _file = discord.File(BytesIO(
                _file), filename="image.gif" if meme.image.content_type == "image/gif" else "image.png")

        await ctx.respond(f"Added new meme!", file=_file or discord.utils.MISSING, embed=await self.prepare_meme_embed(meme))

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Edit an existing meme", permissions=slash_perms.mod_and_up())
    async def editmeme(self, ctx: BlooContext, name: Option(str, autocomplete=memes_autocomplete)) -> None:
        """Edit a meme's body, optionally attach an image.
        
        Example usage
        -------------
        /editmeme roblox this would be the body

        Parameters
        ----------
        name : str
            "Name of meme to edit"
        """

        if len(name.split()) > 1:
            raise commands.BadArgument(
                "Meme names can't be longer than 1 word.")

        name = name.lower()
        meme = guild_service.get_meme(name)
        
        if meme is None:
            raise commands.BadArgument("That meme does not exist.")
        
        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter the content of this meme, and optionally attach an image.",
            convertor=str,
            raw=True)
        description, response = await ctx.prompt(prompt)
        meme.content = description
        
        if len(response.attachments) > 0:
            # ensure the attached file is an image
            image = response.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")
            else:
                image = await image.read()
            
            # save image bytes
            if meme.image is not None:
                meme.image.replace(image, content_type=_type)
            else:
                meme.image.put(image, content_type=_type)
        else:
            meme.image.delete()

        if not guild_service.edit_meme(meme):
            raise commands.BadArgument("An error occurred editing that meme.")
        
        _file = meme.image.read()
        if _file is not None:
            _file = discord.File(BytesIO(_file), filename="image.gif" if meme.image.content_type == "image/gif" else "image.png")
        
        await ctx.respond(f"Meme edited!", file=_file or discord.utils.MISSING, embed=await self.prepare_meme_embed(meme))

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Delete a meme", permissions=slash_perms.mod_and_up())
    async def delmeme(self, ctx: BlooContext, name: Option(str, description="Name of meme to delete", autocomplete=memes_autocomplete)):
        """Delete meme (geniuses only)

        Example usage
        --------------
        /delmeme name:<memename>

        Parameters
        ----------
        name : str
            "Name of meme to delete"

        """

        name = name.lower()

        meme = guild_service.get_meme(name)
        if meme is None:
            raise commands.BadArgument("That meme does not exist.")

        if meme.image is not None:
            meme.image.delete()

        guild_service.remove_meme(name)
        await ctx.send_warning(f"Deleted meme `{meme.name}`.", delete_after=5)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="List all memes")
    async def memelist(self, ctx: BlooContext):
        """List all meemes
        """

        memes = sorted(guild_service.get_guild().memes, key=lambda meme: meme.name)

        if len(memes) == 0:
            raise commands.BadArgument("There are no memes defined.")
        
        menu = Menu(memes, ctx.channel, per_page=12,
                    format_page=format_meme_page, interaction=True, ctx=ctx, whisper=ctx.whisper)

        await menu.start()


    async def prepare_meme_embed(self, meme):
        """Given a meme object, prepare the appropriate embed for it

        Parameters
        ----------
        meme : Meme
            Meme object from database

        Returns
        -------
        discord.Embed
            The embed we want to send
        """
        embed = discord.Embed(title=meme.name)
        embed.description = meme.content
        embed.timestamp = meme.added_date
        embed.color = discord.Color.blue()

        if meme.image.read() is not None:
            embed.set_image(url="attachment://image.gif" if meme.image.content_type ==
                            "image/gif" else "attachment://image.png")
        embed.set_footer(
            text=f"Added by {meme.added_by_tag} | Used {meme.use_count} times")
        return embed

    @editmeme.error
    @meme.error
    @memelist.error
    @delmeme.error
    @addmeme.error
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
    bot.add_cog(Memes(bot))
