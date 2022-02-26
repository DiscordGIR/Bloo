import random
import re
import traceback
from datetime import datetime
from io import BytesIO
from aiohttp import request

import discord
from data.model.tag import Tag
from data.services.guild_service import guild_service
from discord.commands import Option, slash_command, message_command, user_command
from discord.ext import commands
from discord.ext.commands.cooldowns import CooldownMapping
from utils.autocompleters import tags_autocomplete
from utils.config import cfg
from utils.context import BlooContext, PromptData
from utils.logger import logger
from utils.views.menu import Menu
from utils.message_cooldown import MessageTextBucket
from utils.permissions.checks import (PermissionsFailure,
                                      genius_or_submod_and_up, whisper)
from utils.permissions.permissions import permissions
from utils.permissions.slash_perms import slash_perms


def format_tag_page(_, entries, current_page, all_pages):
    embed = discord.Embed(
        title=f'All tags', color=discord.Color.blurple())
    for tag in entries:
        desc = f"Added by: {tag.added_by_tag}\nUsed {tag.use_count} times"
        if tag.image.read() is not None:
            desc += "\nHas image attachment"
        embed.add_field(name=tag.name, value=desc)
    embed.set_footer(
        text=f"Page {current_page} of {len(all_pages)}")
    return embed


def prepare_tag_embed(tag):
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


def prepare_tag_view(tag: Tag):
    if not tag.button_links or tag.button_links is None:
        return

    view = discord.ui.View()
    for label, link in tag.button_links:
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label=label, url=link))

    return view

class TagModal(discord.ui.Modal):
    def __init__(self, tag_name, author: discord.Member) -> None:
        self.tag_name = tag_name
        self.author = author
        self.tag = None

        super().__init__(title=f"Add tag {self.tag_name}")

        self.add_item(
            discord.ui.InputText(
                label="Body of the tag",
                placeholder="Enter the body of the tag",
                style=discord.InputTextStyle.long,
            )
        )
        
        for i in range(2):
            self.add_item(
                discord.ui.InputText(
                    label=f"Button {(i%2)+1} name",
                    placeholder="Enter a name for the button",
                    style=discord.InputTextStyle.short,
                    required=False,
                    max_length=25
                )
            )
            self.add_item(
                discord.ui.InputText(
                    label=f"Button {(i%2)+1} link",
                    placeholder="Enter a link for the button",
                    style=discord.InputTextStyle.short,
                    required=False
                )
            )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return

        button_names = [child.value for child in self.children[1::2] if child.value is not None]
        links = [child.value for child in self.children[2::2] if child.value is not None]

        # make sure all links are valid URLs with regex
        if not all(re.match(r'^(https|http)://.*', link) for link in links):
            embed = discord.Embed(color=discord.Color.red(), description="The links must be valid URLs!")
            await interaction.response.send_message(embeds=[embed], ephemeral=True)
            return

        if len(button_names) != len(links):
            embed = discord.Embed(color=discord.Color.red(), description="All buttons must have labels and links!")
            await interaction.response.send_message(embeds=[embed], ephemeral=True)
            return

        buttons = list(zip(button_names, links))
        description = self.children[0].value
        if not description:
            embed = discord.Embed(color=discord.Color.red(), description="Description is missing!")
            await interaction.response.send_message(embeds=[embed], ephemeral=True)
            return

        # prepare tag data for database
        tag = Tag()
        tag.name = self.tag_name.lower()
        tag.content = description
        tag.added_by_id = self.author.id
        tag.added_by_tag = str(self.author)
        tag.button_links = buttons

        self.tag = tag
        self.stop()
        try:
            await interaction.response.send_message()
        except:
            pass

class EditTagModal(discord.ui.Modal):
    def __init__(self, tag: Tag, author: discord.Member) -> None:
        self.tag = tag
        self.author = author
        self.edited = False

        super().__init__(title=f"Edit tag {self.tag.name}")

        self.add_item(
            discord.ui.InputText(
                label="Body of the tag",
                placeholder="Enter the body of the tag",
                style=discord.InputTextStyle.long,
                value=tag.content
            )
        )
        
        for i in range(2):
            self.add_item(
                discord.ui.InputText(
                    label=f"Button {(i%2)+1} name",
                    placeholder="Enter a name for the button",
                    style=discord.InputTextStyle.short,
                    required=False,
                    max_length=25,
                    value=self.tag.button_links[i][0] if len(self.tag.button_links) > i else None
                )
            )
            self.add_item(
                discord.ui.InputText(
                    label=f"Button {(i%2)+1} link",
                    placeholder="Enter a link for the button",
                    style=discord.InputTextStyle.short,
                    required=False,
                    value=self.tag.button_links[i][1] if len(self.tag.button_links) > i else None
                )
            )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return

        button_names = [child.value for child in self.children[1::2] if child.value is not None]
        links = [child.value for child in self.children[2::2] if child.value is not None]

        # make sure all links are valid URLs with regex
        if not all(re.match(r'^(https|http)://.*', link) for link in links):
            embed = discord.Embed(color=discord.Color.red(), description="The links must be valid URLs!")
            await interaction.response.send_message(embeds=[embed], ephemeral=True)
            return

        if len(button_names) != len(links):
            embed = discord.Embed(color=discord.Color.red(), description="All buttons must have labels and links!")
            await interaction.response.send_message(embeds=[embed], ephemeral=True)
            return

        description = self.children[0].value
        if not description:
            embed = discord.Embed(color=discord.Color.red(), description="Description is missing!")
            await interaction.response.send_message(embeds=[embed], ephemeral=True)
            return

        buttons = list(zip(button_names, links))
        description = self.children[0].value

        # prepare tag data for database
        self.tag.content = description
        self.tag.button_links = buttons
        self.edited = True
        self.stop()

        try:
            await interaction.response.send_message()
        except:
            pass

class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tag_cooldown = CooldownMapping.from_cooldown(
            1, 5, MessageTextBucket.custom)

        self.support_tags = [tag.name for tag in guild_service.get_guild(
        ).tags if tag.name in ["support", "support2", "support3"]]

    @slash_command(guild_ids=[cfg.guild_id], description="Display a tag")
    async def tag(self, ctx: BlooContext, name: Option(str, description="Tag name", autocomplete=tags_autocomplete), user_to_mention: Option(discord.Member, description="User to mention in the response", required=False)):
        """Displays a tag.

        Example usage
        -------------
        /tag name:<tagname>

        Parameters
        ----------
        name : str
            "Name of tag to display"

        """
        name = name.lower()
        tag = guild_service.get_tag(name)

        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        # run cooldown so tag can't be spammed
        bucket = self.tag_cooldown.get_bucket(tag.name)
        current = datetime.now().timestamp()
        # ratelimit only if the invoker is not a moderator
        if bucket.update_rate_limit(current) and not (permissions.has(ctx.guild, ctx.author, 5) or ctx.guild.get_role(guild_service.get_guild().role_sub_mod) in ctx.author.roles):
            raise commands.BadArgument("That tag is on cooldown.")

        # if the Tag has an image, add it to the embed
        file = tag.image.read()
        if file is not None:
            file = discord.File(BytesIO(
                file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")

        if user_to_mention is not None:
            title = f"Hey {user_to_mention.mention}, have a look at this!"
        else:
            title = None

        await ctx.respond(content=title, embed=prepare_tag_embed(tag), view=prepare_tag_view(tag), file=file)

    @user_command(guild_ids=[cfg.guild_id], name="Support tag")
    async def support_tag_rc(self, ctx: BlooContext, user: discord.Member) -> None:
        await self.handle_support_tag(ctx, user)

    @message_command(guild_ids=[cfg.guild_id], name="Support tag")
    async def support_tag_msg(self, ctx: BlooContext, message: discord.Message) -> None:
        await self.handle_support_tag(ctx, message.author)

    async def handle_support_tag(self, ctx: BlooContext, member: discord.Member) -> None:
        if not self.support_tags:
            raise commands.BadArgument("No support tags found.")

        random_tag = random.choice(self.support_tags)
        tag = guild_service.get_tag(random_tag)

        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        # run cooldown so tag can't be spammed
        bucket = self.tag_cooldown.get_bucket(tag.name)
        current = datetime.now().timestamp()
        # ratelimit only if the invoker is not a moderator
        if bucket.update_rate_limit(current) and not (permissions.has(ctx.guild, ctx.author, 5) or ctx.guild.get_role(guild_service.get_guild().role_sub_mod) in ctx.author.roles):
            raise commands.BadArgument("That tag is on cooldown.")

        # if the Tag has an image, add it to the embed
        file = tag.image.read()
        if file is not None:
            file = discord.File(BytesIO(
                file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")

        title = f"Hey {member.mention}, have a look at this!"
        await ctx.respond(content=title, embed=prepare_tag_embed(tag), file=file)

    @genius_or_submod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Display a tag", permissions=slash_perms.genius_or_submod_and_up())
    async def rawtag(self, ctx: BlooContext, name: Option(str, description="Tag name", autocomplete=tags_autocomplete), mobile_friendly: Option(bool, description="Whether to display the tag in a mobile friendly format")):
        """Post raw body of a tag

        Example usage
        -------------
        !rawtag roblox

        Parameters
        ----------
        name : str
            "Name of tag to use"
        """

        name = name.lower()
        tag = guild_service.get_tag(name)

        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        # if the Tag has an image, add it to the embed
        file = tag.image.read()
        if file is not None:
            file = discord.File(BytesIO(
                file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")

        response = discord.utils.escape_markdown(tag.content) if not mobile_friendly else tag.content
        parts = [response[i:i+2000] for i in range(0, len(response), 2000)]

        for i, part in enumerate(parts):
            if i == 0:
                await ctx.respond(part, file=file if i == len(parts) - 1 else None, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))
            else:
                await ctx.send(part, file=file if i == len(parts) - 1 else None, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="List all tags")
    async def taglist(self, ctx: BlooContext):
        """List all tags
        """

        _tags = sorted(guild_service.get_guild().tags, key=lambda tag: tag.name)

        if len(_tags) == 0:
            raise commands.BadArgument("There are no tags defined.")

        menu = Menu(ctx, _tags, per_page=12, page_formatter=format_tag_page, whisper=ctx.whisper)
        await menu.start()

    tags = discord.SlashCommandGroup("tags", "Interact with tags", guild_ids=[cfg.guild_id], permissions=slash_perms.genius_or_submod_and_up())

    @genius_or_submod_and_up()
    @tags.command(guild_ids=[cfg.guild_id], description="Add a new tag")
    async def add(self, ctx: BlooContext, name: Option(str, description="Name of the new tag"), image: Option(discord.Attachment, required=False, description="Image to show in tag")) -> None:
        """Add a tag. Optionally attach an image. (Genius only)

        Example usage
        -------------
        /addtag roblox

        Parameters
        ----------
        name : str
            "Name of the tag"

        """

        if not name.isalnum():
            raise commands.BadArgument("Tag name must be alphanumeric.")

        if len(name.split()) > 1:
            raise commands.BadArgument(
                "Tag names can't be longer than 1 word.")

        if (guild_service.get_tag(name.lower())) is not None:
            raise commands.BadArgument("Tag with that name already exists.")

        content_type = None
        if image is not None:
            # ensure the attached file is an image
            content_type = image.content_type
            if content_type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")

            image = await image.read()

        modal = TagModal(tag_name=name, author=ctx.author)
        await ctx.interaction.response.send_modal(modal)
        await modal.wait()

        tag = modal.tag
        if tag is None:
            await ctx.send_warning("Tag creation was cancelled.")

         # did the user want to attach an image to this tag?
        if image is not None:
            tag.image.put(image, content_type=content_type)

        # store tag in database
        guild_service.add_tag(tag)

        _file = tag.image.read()
        if _file is not None:
            _file = discord.File(BytesIO(
                _file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")

        await ctx.followup.send(f"Added new tag!", file=_file or discord.MISSING, embed=prepare_tag_embed(tag) or discord.MISSING, view=prepare_tag_view(tag) or discord.MISSING, delete_after=5)


    @genius_or_submod_and_up()
    @tags.command(guild_ids=[cfg.guild_id], description="Edit an existing tag")
    async def edit(self, ctx: BlooContext, name: Option(str, autocomplete=tags_autocomplete), image: Option(discord.Attachment, required=False)) -> None:
        """Edit a tag's body, optionally attach an image.

        Example usage
        -------------
        !edittag roblox this would be the body

        Parameters
        ----------
        name : str
            "Name of tag to edit"
        """

        if len(name.split()) > 1:
            raise commands.BadArgument(
                "Tag names can't be longer than 1 word.")

        name = name.lower()
        tag = guild_service.get_tag(name)

        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        content_type = None
        if image is not None:
            # ensure the attached file is an image
            content_type = image.content_type
            if content_type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")

            image = await image.read()

            # save image bytes
            if tag.image is not None:
                tag.image.replace(image, content_type=content_type)
            else:
                tag.image.put(image, content_type=content_type)
        else:
            tag.image.delete()

        modal = EditTagModal(tag=tag, author=ctx.author)
        await ctx.interaction.response.send_modal(modal)
        await modal.wait()

        if not modal.edited: 
            await ctx.send_warning("Tag edit was cancelled.")
            return

        tag = modal.tag

        # store tag in database
        guild_service.edit_tag(tag)

        _file = tag.image.read()
        if _file is not None:
            _file = discord.File(BytesIO(
                _file), filename="image.gif" if tag.image.content_type == "image/gif" else "image.png")

        await ctx.followup.send(f"Edited tag!", file=_file or discord.MISSING, embed=prepare_tag_embed(tag), view=prepare_tag_view(tag) or discord.MISSING, delete_after=5)


    @genius_or_submod_and_up()
    @tags.command(guild_ids=[cfg.guild_id], description="Delete a tag")
    async def delete(self, ctx: BlooContext, name: Option(str, description="Name of tag to delete", autocomplete=tags_autocomplete)):
        """Delete tag (geniuses only)

        Example usage
        --------------
        /deltag name:<tagname>

        Parameters
        ----------
        name : str
            "Name of tag to delete"

        """

        name = name.lower()

        tag = guild_service.get_tag(name)
        if tag is None:
            raise commands.BadArgument("That tag does not exist.")

        if tag.image is not None:
            tag.image.delete()

        guild_service.remove_tag(name)
        await ctx.send_warning(f"Deleted tag `{tag.name}`.", delete_after=5)

    @edit.error
    @tag.error
    @support_tag_msg.error
    @support_tag_rc.error
    @rawtag.error
    @taglist.error
    @delete.error
    @add.error
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
    bot.add_cog(Tags(bot))
