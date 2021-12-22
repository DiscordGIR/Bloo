import discord
from discord.commands import Option, slash_command
from discord.ext import commands

import traceback
from data.services.guild_service import guild_service
from utils.config import cfg
from utils.context import BlooContext, PromptData, PromptDataReaction
from utils.permissions.checks import PermissionsFailure, admin_and_up
from utils.permissions.slash_perms import slash_perms
from utils.logger import logger
from utils.views.role_buttons import ReactionRoleButton

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
            view = discord.ui.View(timeout=None)
            for emoji, role in mapping.items():
                role = guild.get_role(role)
                view.add_item(ReactionRoleButton(role, emoji))

            self.bot.add_view(view)

    buttons = discord.SlashCommandGroup("buttons", "Interact with role buttons", permissions=slash_perms.admin_and_up())

    @admin_and_up()
    @buttons.command(description="Post the button role assignment message")
    async def post_message(self, ctx: BlooContext):
        # timeout is None because we want this view to be persistent
        channel = ctx.guild.get_channel(
            guild_service.get_guild().channel_reaction_roles)
        if channel is None:
            raise commands.BadArgument("Role assignment channel not found!")

        embed = discord.Embed(
            description="Click the buttons to opt-in to or opt-out of notifications of your choice. ", color=discord.Color.blurple())
        await channel.send(embed=embed)
        await ctx.send_success(f"Posted in {channel.mention}!")

    @admin_and_up()
    @buttons.command(name="set", description="Prompt to add role assignment buttons to a message")
    async def _set(self, ctx: BlooContext, message_id: str):
        """Prompt to add multiple reaction roles to a message (admin only)

        Example usage
        -------------
        /buttons set <message ID>

        Parameters
        ----------
        message_id : int
            "ID of message to add reactions to"
        """

        message_id = int(message_id)
        request_role_channel = ctx.guild.get_channel(
            guild_service.get_guild().channel_reaction_roles)

        if request_role_channel is None:
            return

        message = None
        try:
            message = await request_role_channel.fetch_message(message_id)
        except Exception:
            raise commands.BadArgument("Message not found.")
        
        if message.author != ctx.me:
            raise commands.BadArgument("Message must be sent by me, use `/postembed` or `/postbuttonmessage`")

        reaction_mapping = {message.id: {}}

        await ctx.defer()
        while True:
            reaction = await self.prompt_for_reaction(ctx, reaction_mapping[message.id])

            if reaction is None:
                await ctx.send_warning("Timed out waiting for reaction, cancelling.", delete_after=5)
                return
            elif str(reaction.emoji) == "✅":
                break

            role = await self.prompt_for_role(ctx, reaction, reaction_mapping[message.id])
            if role is None:
                await ctx.send_warning("Cancelled setting reactions.", delete_after=5)
                return

            reaction_mapping[message.id][str(reaction.emoji)] = role.id

        if not reaction_mapping[message.id].keys():
            raise commands.BadArgument("Nothing to do.")

        guild_service.add_rero_mapping(reaction_mapping)

        view = discord.ui.View(timeout=None)
        resulting_reactions_list = ""
        async with ctx.channel.typing():
            for r in reaction_mapping[message.id]:
                resulting_reactions_list += f"Reaction {r} will give role <@&{reaction_mapping[message.id][r]}>\n"
                view.add_item(ReactionRoleButton(
                    ctx.guild.get_role(reaction_mapping[message.id][r]), r))
            await message.edit(view=view)

        await ctx.send_success(title="Reaction roles set!", description=resulting_reactions_list)

    @admin_and_up()
    @buttons.command(description="Add a new role assignment button to a message")
    async def add(self, ctx: BlooContext, message_id: str):
        """Add one new reaction to a given message

        Example usage
        -------------
        /buttons add <message ID>

        Parameters
        ----------
        message : int
            "Message to add reaction to"
        """

        try:
            message_id = int(message_id)
        except Exception:
            raise commands.BadArgument("Message ID must be an int")

        channel = ctx.guild.get_channel(
            guild_service.get_guild().channel_reaction_roles)

        if channel is None:
            return

        current =  guild_service.get_rero_mapping(str(message_id))
        if current is None:
            raise commands.BadArgument(
                f"Message with ID {message_id} had no reactions set in database. Use `/setbuttons` first.")

        reaction_mapping = dict(current)

        message = None
        try:
            message = await channel.fetch_message(message_id)
        except Exception:
            raise commands.BadArgument("Message not found.")

        if message.author != ctx.me:
            raise commands.BadArgument("Message must be sent by me, use `/postembed` or `/postbuttonmessage`")

        await ctx.defer()
        while True:
            reaction = await self.prompt_for_reaction(ctx, reaction_mapping)

            if reaction is None:
                await ctx.send_warning("Timed out waiting for reaction, cancelling.", delete_after=5)
                return
            elif str(reaction.emoji) in reaction_mapping:
                raise commands.BadArgument(
                    f"Reaction {str(reaction)} is already in use on that message.")
            elif str(reaction.emoji) == "✅":
                await ctx.send_warning("Cancelled adding new reaction.", delete_after=5)
                return

            role = await self.prompt_for_role(ctx, reaction, reaction_mapping)
            if role is None:
                await ctx.send_warning("Cancelled setting reactions.", delete_after=5)
                return
            elif role.id in reaction_mapping.values():
                raise commands.BadArgument(
                    f"There is already a reaction for {role.mention} on that message.")

            reaction_mapping[str(reaction.emoji)] = role.id
            break

        guild_service.append_rero_mapping(message_id, reaction_mapping)

        view = discord.ui.View(timeout=None)
        resulting_reactions_list = ""
        async with ctx.channel.typing():
            for r in reaction_mapping:
                resulting_reactions_list += f"Reaction {r} will give role <@&{reaction_mapping[r]}>\n"
                view.add_item(ReactionRoleButton(
                    ctx.guild.get_role(reaction_mapping[r]), r))
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

        prompt_role = PromptData(value_name="role to give", description=text,
                                 convertor=commands.converter.RoleConverter().convert)

        return await ctx.prompt(prompt_role)

    @admin_and_up()
    @buttons.command(description="Move buttons from one message to another")
    async def move(self, ctx: BlooContext, before: Option(str, description="ID of the old message"), after: Option(str, description="ID of the new message")):
        """Move reactions from one message to another.

        Example use
        -----------
        /buttons move <before message ID> <after message ID>

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

        channel = ctx.guild.get_channel(
            guild_service.get_guild().channel_reaction_roles)

        if channel is None:
            return

        rero_mapping = guild_service.get_rero_mapping(str(before))
        if rero_mapping is None:
            raise commands.BadArgument(
                f"Message with ID {before} had no reactions set in database.")

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
        view = discord.ui.View(timeout=None)
        async with ctx.channel.typing():
            for r in rero_mapping[after]:
                resulting_reactions_list += f"Reaction {r} will give role <@&{rero_mapping[after][r]}>\n"
                view.add_item(ReactionRoleButton(
                    ctx.guild.get_role(rero_mapping[after][r]), r))
            await after_message.edit(view=view)

        await ctx.send_success(title="Reaction roles moved!", description=resulting_reactions_list)

    @admin_and_up()
    @buttons.command(description="Repost all buttons")
    async def repost(self, ctx: BlooContext):
        """Repost all reactions to messages with reaction roles (admin only)
        """

        channel = ctx.guild.get_channel(
            guild_service.get_guild().channel_reaction_roles)

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
                view = discord.ui.View(timeout=None)
                for r in rero_mapping[m]:
                    role = ctx.guild.get_role(rero_mapping[m][r])
                    view.add_item(ReactionRoleButton(role, r))
                await message.edit(view=view)

        await ctx.send_success("Done!")

    @move.error
    @add.error
    @_set.error
    @post_message.error
    @repost.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, discord.ApplicationCommandInvokeError):
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
            logger.error(traceback.format_exc())


def setup(bot):
    bot.add_cog(RoleAssignButtons(bot))
