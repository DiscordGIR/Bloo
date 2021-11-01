import discord
from discord import components
from discord.commands import Option, slash_command
from discord.enums import ButtonStyle
from discord.ext import commands
from discord.interactions import Interaction
from utils.permissions.checks import mod_and_up, whisper
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.slash_perms  import slash_perms
from discord import ui
"""
Make sure to add the cog to the initial_extensions list
in main.py
"""

emojis = {
    "<:gircoin:846511056137748571>": "846383888003760217",
    "<a:GirDance:846510964463239199>": "846383888036134932"
}

class ReactionRoleButton(ui.Button):
    def __init__(self, role: discord.Role, emoji):
        super().__init__(label=role.name, style=ButtonStyle.primary, emoji=emoji, custom_id=str(role.id))
        self.emoji = emoji
    
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

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @whisper()
    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Post the reaction role message", permissions=slash_perms.mod_and_up())
    async def post(self, ctx: BlooContext):
        # timeout is None because we want this view to be persistent
        view = ui.View(timeout=None)
        
        # loop through the dict of roles and add them to the view
        for emoji, role_id in emojis.items():
            role = ctx.guild.get_role(int(role_id))
            view.add_item(ReactionRoleButton(role, emoji))

        await ctx.respond("Click a button to assign yourself a role", view=view)
        
    @commands.Cog.listener()
    async def on_ready(self):
        # this function is run when the bot is started.
        # we recreate the view as we did in the /post command
        view = ui.View(timeout=None)
        guild = self.bot.get_guild(cfg.guild_id)
        for emoji, role_id in emojis.items():
            role = guild.get_role(int(role_id))
            view.add_item(ReactionRoleButton(role, emoji))

        # add the view to the bot so it will watch for reactions
        self.bot.add_view(view)

def setup(bot):
    bot.add_cog(ReactionRoles(bot))
