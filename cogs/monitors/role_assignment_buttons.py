import re
import traceback
from itertools import takewhile

import discord
from services import guild_service
from discord import ui
from discord.commands import Option, slash_command
from discord.ext import commands
from discord.interactions import Interaction
from utils import BlooContext, PromptData, PromptDataReaction, cfg
from utils.permissions import PermissionsFailure, admin_and_up, slash_perms


def derive_label(string):
    enders = {
        "AppleEventNews": " ",
        "SubredditNews": " ",
        "CommunityEvents": " ",
        "CommunityEvents": " ",
        "Giveaway": "Notifications",
        
    }
    starter = str("".join(list(takewhile(lambda x: x.islower(), string))))
    middle = " ".join(re.findall(r'[A-Z0-9](?:[a-z0-9]+|[A-Z0-9]*(?=[A-Z0-9]|$))', string))
    return f"{starter}{middle} {enders.get(string) or 'Updates'}"


class ReactionRoleButton(ui.Button):
    def __init__(self, role: discord.Role, emoji: discord.Emoji):
        super().__init__(label=derive_label(role.name), style=discord.ButtonStyle.primary, emoji=emoji, custom_id=str(role.id))
    
    async def callback(self, interaction: Interaction):
        user = interaction.user
        role = interaction.guild.get_role(int(self.custom_id))
        if role is None:
            return
        
        if role not in user.roles:
            await user.add_roles(role)
            await interaction.response.send_message(f"{self.emoji} You have been given the role {role.mention}", ephemeral=True)
        else:
            await user.remove_roles(role)
            await interaction.response.send_message(f"{self.emoji} You have been removed the role {role.mention}", ephemeral=True)

class RoleAssignButtons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        # this function is run when the bot is started.
        # we recreate the view as we did in the /post command
        guild = self.bot.get_guild(cfg.guild_id)
        rero_mappings = guild_service.all_rero_mappings()
        for _, mapping in rero_mappings.items():
            view = ui.View(timeout=None)
            for emoji, role in mapping.items():
                role = guild.get_role(role)
                view.add_item(ReactionRoleButton(role, emoji))

            self.bot.add_view(view)

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Post the button role assignment message", permissions=slash_perms.admin_and_up())
    async def postbuttonmessage(self, ctx: BlooContext):
        # timeout is None because we want this view to be persistent
        channel = ctx.guild.get_channel(guild_service.get_guild().channel_reaction_roles)
        if channel is None:
            raise commands.BadArgument("Role assignment channel not found!")

        embed = discord.Embed(description="Click the buttons to opt-in to notifications of your choice. ", color=discord.Color.blurple())
        await channel.send(embed=embed)
        await ctx.send_success(f"Posted in {channel.mention}!")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Prompt to add role assignment buttons to a message", permissions=slash_perms.admin_and_up())
    async def setbuttons(self, ctx: BlooContext, message_id: str):
        """Prompt to add multiple reaction roles to a message (admin only)

        Example usage
        -------------
        !setbuttons <message ID>

        Parameters
        ----------
        message_id : int
            "ID of message to add reactions to"
        """

        message_id = int(message_id)
        request_role_channel = ctx.guild.get_channel(guild_service.get_guild().channel_reaction_roles)

        if request_role_channel is None:
            return

        message = None
        try:
            message = await request_role_channel.fetch_message(message_id)
        except Exception:
            raise commands.BadArgument("Message not found.")

        reaction_mapping = {message.id: {}}
        
        await ctx.defer()
        while True:
            reaction = await self.prompt_for_reaction(ctx, reaction_mapping[message.id])
            
            if reaction is None:
                await ctx.send_warning("Timed out waiting for reaction, cancelling.")
                return
            elif str(reaction.emoji) == "✅":
                break
            elif isinstance(reaction.emoji, discord.PartialEmoji) or (isinstance(reaction.emoji, discord.Emoji) and not reaction.emoji.available):
                await ctx.respond_or_edit(embed=discord.Embed(description="That emoji is not available to me :(", color=discord.Color.dark_orange()), delete_after=5)
                continue
            
            role = await self.prompt_for_role(ctx, reaction, reaction_mapping[message.id])
            if role is None:
                await ctx.send_warning("Cancelled setting reactions.")
                return
            
            reaction_mapping[message.id][str(reaction.emoji)] = role.id

        if not reaction_mapping[message.id].keys():
            raise commands.BadArgument("Nothing to do.")

        guild_service.add_rero_mapping(reaction_mapping)

        view = ui.View(timeout=None)
        resulting_reactions_list = ""
        async with ctx.channel.typing():
            for r in reaction_mapping[message.id]:
                resulting_reactions_list += f"Reaction {r} will give role <@&{reaction_mapping[message.id][r]}>\n"
                view.add_item(ReactionRoleButton(ctx.guild.get_role(reaction_mapping[message.id][r]), r))
            await message.edit(view=view)

        await ctx.send_success(title="Reaction roles set!", description=resulting_reactions_list)

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Add a new role assignment button to a message", permissions=slash_perms.admin_and_up())
    async def addbutton(self, ctx: BlooContext, message_id: str):
        """Add one new reaction to a given message

        Example usage
        -------------
        !addbutton <message ID>

        Parameters
        ----------
        message : int
            "Message to add reaction to"
        """

        message_id = int(message_id)

        channel = ctx.guild.get_channel(guild_service.get_guild().channel_reaction_roles)

        if channel is None:
            return

        reaction_mapping = dict(guild_service.get_rero_mapping(str(message_id)))
        if reaction_mapping is None:
            raise commands.BadArgument(f"Message with ID {message_id} had no reactions set in database. Use `!setreactions` first.")

        message = None
        try:
            message = await channel.fetch_message(message_id)
        except Exception:
            raise commands.BadArgument("Message not found.")
        
        await ctx.defer()
        while True:
            reaction = await self.prompt_for_reaction(ctx, reaction_mapping)
            
            if reaction is None:
                await ctx.send_warning("Timed out waiting for reaction, cancelling.")
                return
            elif str(reaction.emoji) in reaction_mapping:
                raise commands.BadArgument(f"Reaction {str(reaction)} is already in use on that message.")
            elif str(reaction.emoji) == "✅":
                await ctx.send_warning("Cancelled adding new reaction.")
                return
            elif isinstance(reaction.emoji, discord.PartialEmoji) or (isinstance(reaction.emoji, discord.Emoji) and not reaction.emoji.available):
                await ctx.send_warning("That emoji is not available to me :(",)
                continue
            
            role = await self.prompt_for_role(ctx, reaction, reaction_mapping)
            if role is None:
                await ctx.send_warning("Cancelled setting reactions.")
                return
            elif role.id in reaction_mapping.values():
                raise commands.BadArgument(f"There is already a reaction for {role.mention} on that message.")
            
            reaction_mapping[str(reaction.emoji)] = role.id
            break

        guild_service.append_rero_mapping(message_id, reaction_mapping)
        
        view = ui.View(timeout=None)
        resulting_reactions_list = ""
        async with ctx.channel.typing():
            for r in reaction_mapping:
                resulting_reactions_list += f"Reaction {r} will give role <@&{reaction_mapping[r]}>\n"
                view.add_item(ReactionRoleButton(ctx.guild.get_role(reaction_mapping[r]), r))
            await message.edit(view=view)
        await ctx.send_success(title="Added new reaction!", description=resulting_reactions_list)

    async def prompt_for_reaction(self, ctx, reactions):
        text = "Please add the reaction to this message that you want to watch for (or :white_check_mark: to finish or cancel if nothing set so far)"
        if reactions:
            text += "\n\n**Current reactions**"
            for r in reactions:
                text += f"\n{r} <@&{reactions[r]}>"

        prompt_reaction_message = await ctx.send_success(description=text, title="Reaction roles")
        prompt_reaction = PromptDataReaction(
            message=prompt_reaction_message, 
            reactions=[], 
            timeout=30, 
            raw_emoji=True)
        
        reaction, _ = await ctx.prompt_reaction(prompt_reaction)
        return reaction
    
    async def prompt_for_role(self, ctx, current_reaction, reactions):
        text = f"Please enter a role ID to use for {current_reaction} (or 'cancel' to stop)"
        if reactions:
            text += "\n\n**Current reactions**"
            for r in reactions:
                text += f"\n{r} <@&{reactions[r]}>"

        prompt_role = PromptData(value_name="role to give", 
                                            description=text, 
                                            convertor=commands.converter.RoleConverter().convert)
        
        return await ctx.prompt(prompt_role)

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Move buttons from one message to another", permissions=slash_perms.admin_and_up())
    async def movebuttons(self, ctx: BlooContext, before: Option(str, description="ID of the old message"), after: Option(str, description="ID of the new message")):
        """Move reactions from one message to another.

        Example use
        -----------
        !movereactions <before message ID> <after message ID>

        Parameters
        ----------
        before : int
            "ID of before messsage"
        after : int
            "ID of after message"
        """

        before, after = int(before), int(after)

        if before == after:
            raise commands.BadArgument("I can't move to the same message.")

        channel = ctx.guild.get_channel(guild_service.get_guild().channel_reaction_roles)

        if channel is None:
            return

        rero_mapping = guild_service.get_rero_mapping(str(before))
        if rero_mapping is None:
            raise commands.BadArgument(f"Message with ID {before} had no reactions set in database.")

        try:
            after_message = await channel.fetch_message(after)
        except Exception:
            raise commands.BadArgument(f"Message with ID {after} not found.")

        try:
            before_message = await channel.fetch_message(before)
        except Exception:
            raise commands.BadArgument(f"Message with ID {before} not found.")

        rero_mapping = {after: rero_mapping}

        guild_service.add_rero_mapping(rero_mapping)
        guild_service.delete_rero_mapping(before)

        await before_message.edit(view=None)

        resulting_reactions_list = "Done! We added the following emotes:\n"
        view = ui.View(timeout=None)
        async with ctx.channel.typing():
            for r in rero_mapping[after]:
                resulting_reactions_list += f"Reaction {r} will give role <@&{rero_mapping[after][r]}>\n"
                view.add_item(ReactionRoleButton(ctx.guild.get_role(rero_mapping[after][r]), r))
            await after_message.edit(view=view)

        await ctx.send_success(title="Reaction roles moved!", description=resulting_reactions_list)

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Repost all buttons", permissions=slash_perms.admin_and_up())
    async def repostbuttons(self, ctx: BlooContext):
        """Repost all reactions to messages with reaction roles (admin only)
        """

        channel = ctx.guild.get_channel(guild_service.get_guild().channel_reaction_roles)

        if channel is None:
            return

        rero_mapping = guild_service.all_rero_mappings()
        if rero_mapping is None or rero_mapping == {}:
            raise commands.BadArgument("Nothing to do.")

        async with ctx.channel.typing():
            for m in rero_mapping:
                try:
                    message = await channel.fetch_message(int(m))
                except Exception:
                    continue
                view = ui.View(timeout=None)
                for r in rero_mapping[m]:
                    role = ctx.guild.get_role(rero_mapping[m][r])
                    view.add_item(ReactionRoleButton(role, r))
                await message.edit(view=view)

        await ctx.send_success("Done!")


    @movebuttons.error
    @addbutton.error
    @setbuttons.error
    @postbuttonmessage.error
    @repostbuttons.error
    async def info_error(self,  ctx: BlooContext, error):
        error = error.original
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error(error)
            traceback.print_exc()


def setup(bot):
    bot.add_cog(RoleAssignButtons(bot))
