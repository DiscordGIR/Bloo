from discord import ui
from discord.enums import ButtonStyle
from discord.interactions import Interaction
from discord.ext.commands import Context
from discord.member import Member
from utils.permissions import permissions


class ReportActions(ui.View):
    def __init__(self, author: Member):
        super().__init__()
        self.author = author

    async def start(self, ctx: Context):
        self.ctx = ctx
        await self.wait()
        
    def check(self, interaction: Interaction):
        if not permissions.has(self.author.guild, interaction.user, 5):
            return False
        return True

    @ui.button(emoji="✅", label="Dismiss", style=ButtonStyle.primary)
    async def dismiss(self, button: ui.Button, interaction: Interaction):
        if not self.check(interaction):
            return
        await self.ctx.message.delete()
        
    @ui.button(emoji="🆔", label="Post ID", style=ButtonStyle.primary)
    async def id(self, button: ui.Button, interaction: Interaction):
        if not self.check(interaction):
            return
        await self.ctx.channel.send(self.author.id)

    @ui.button(emoji="🧹", label="Clean up", style=ButtonStyle.primary)
    async def purge(self, button: ui.Button, interaction: Interaction):
        if not self.check(interaction):
            return
        await self.ctx.channel.purge(limit=100)

