import discord
from discord.colour import Color
from discord.embeds import Embed
from data.services.guild_service import guild_service
from discord import components
from discord.commands import Option, slash_command
from discord.enums import ButtonStyle
from discord.ext import commands
from discord.interactions import Interaction, InteractionMessage
from utils.permissions.checks import PermissionsFailure, admin_and_up, mod_and_up, whisper
from utils.config import cfg
from utils.context import BlooContext, PromptData, PromptDataReaction
from utils.permissions.slash_perms  import slash_perms
from discord import ui
import traceback
"""
Make sure to add the cog to the initial_extensions list
in main.py
"""


class ReactionRoleButton(ui.Button):
    def __init__(self, role: discord.Role, emoji: discord.Emoji):
        super().__init__(label=role.name, style=ButtonStyle.primary, emoji=emoji, custom_id=str(role.id))
    
    async def callback(self, interaction: Interaction):
        user = interaction.user
        role = interaction.gui846383888053567513ld.get_role(int(self.custom_id))
        if role is None:
            return
        
        if role not in user.roles:
            await user.add_roles(role)
            await interaction.response.send_message(f"{self.emoji} You have been given the role {role.mention}", ephemeral=True)
        else:
            await user.remove_roles(role)
            await interaction.response.send_message(f"{self.emoji} You have been removed the role {role.mention}", ephemeral=True)

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Post the button role messages", permissions=slash_perms.admin_and_up())
    async def postreact(self, ctx: BlooContext):
        # timeout is None because we want this view to be persistent
        channel = ctx.guild.get_channel(guild_service.get_guild().channel_reaction_roles)
        if channel is None:
            raise commands.BadArgument("Reaction role channel not found!")

        embed = Embed(description="Click the buttons to opt-in to notifications of your choice. ", color=Color.blurple())
        await channel.send(embed=embed)
        await ctx.send_success(f"Posted in {channel.mention}!")

    @slash_command(guild_ids=[cfg.guild_id], description="Prompt to add multiple reaction roles to a message", permissions=slash_perms.admin_and_up())
    async def setreactions(self, ctx: BlooContext, message_id: str):
        """Prompt to add multiple reaction roles to a message (admin only)

        Example usage
        -------------
        !setreactions <message ID>

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
                await ctx.send_warning("Timed out waiting for reaction, cancelling.", delete_after=5)
                return
            elif str(reaction.emoji) == "✅":
                break
            elif isinstance(reaction.emoji, discord.PartialEmoji) or (isinstance(reaction.emoji, discord.Emoji) and not reaction.emoji.available):
                await ctx.respond_or_edit(embed=discord.Embed(description="That emoji is not available to me :(", color=discord.Color.dark_orange()), delete_after=5)
                continue
            
            role = await self.prompt_for_role(ctx, reaction, reaction_mapping[message.id])
            if role is None:
                await ctx.send_warning("Cancelled setting reactions.", delete_after=5)
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

    async def prompt_for_reaction(self, ctx, reactions):
        text = "Please add the reaction to this message that you want to watch for (or :white_check_mark: to finish or cancel if nothing set so far)"
        if reactions:
            text += "\n\n**Current reactions**"
            for r in reactions:
                text += f"\n{r} <@&{reactions[r]}>"

        prompt_reaction_message = await ctx.send_success(description=text, title="Reaction roles")
        print(type(prompt_reaction_message))
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
            
            # for role in guild.roles[:25]:
            # view.add_item(ReactionRoleButton(role))
            self.bot.add_view(view)

        # add the view to the bot so it will watch for reactions
        # self.bot.add_view(view)
        
    @setreactions.error
    @postreact.error
    async def info_error(self,  ctx: BlooContext, error):
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
    bot.add_cog(ReactionRoles(bot))
