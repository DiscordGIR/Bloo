import discord

import re
from itertools import takewhile


class ReactionRoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role, emoji: discord.Emoji):
        super().__init__(label=role.name, style=discord.ButtonStyle.primary, emoji=emoji, custom_id=str(role.id))

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        role = interaction.guild.get_role(int(self.custom_id))
        if role is None:
            return

        if role not in user.roles:
            await user.add_roles(role)
            await interaction.response.send_message(f"{self.emoji} You have been given the role {role.mention}", ephemeral=True)
        else:
            await user.remove_roles(role)
            await interaction.response.send_message(f"{self.emoji} You have removed the {role.mention} role", ephemeral=True)
