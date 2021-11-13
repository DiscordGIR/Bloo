import discord
from discord import ui
from discord.ext import commands
from utils.context import BlooContext, PromptData


class WarnView(ui.View):
    def __init__(self, ctx: BlooContext, member: discord.Member, warn):
        super().__init__()
        self.member = member
        self.warn = warn
        self.ctx = ctx

    def check(self, interaction: discord.Interaction):
        if not self.ctx.author == interaction.user:
            return False
        return True

    @ui.button(label="50", style=discord.ButtonStyle.primary)
    async def fifty(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        reason = await self.prompt_reason(interaction)
        if reason is None:
            await self.ctx.send_warning("Cancelled")
            return

        await self.warn(self.ctx, self.member, 50, reason)

    @ui.button(label="100", style=discord.ButtonStyle.primary)
    async def hundred(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        reason = await self.prompt_reason(interaction)
        if reason is None:
            await self.ctx.send_warning("Cancelled")
            return

        await self.warn(self.ctx, self.member, 100, reason)

    @ui.button(label="150", style=discord.ButtonStyle.primary)
    async def hun_fifty(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        reason = await self.prompt_reason(interaction)
        if reason is None:
            await self.ctx.send_warning("Cancelled")
            return

        await self.warn(self.ctx, self.member, 150, reason)
    
    @ui.button(label="200", style=discord.ButtonStyle.primary)
    async def two_hun(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        reason = await self.prompt_reason(interaction)
        if reason is None:
            await self.ctx.send_warning("Cancelled")
            return

        await self.warn(self.ctx, self.member, 200, reason)

    @ui.button(emoji="❌", style=discord.ButtonStyle.primary)
    async def cancel(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.send_warning("Cancelled")

    async def prompt_reason(self, interaction: discord.Interaction):
        prompt_data = PromptData(value_name="Reason", 
                                        description="Reason for warn?",
                                        convertor=str,
                                        )
        await interaction.response.defer()
        self.ctx.author = interaction.user
        reason = await self.ctx.prompt(prompt_data)
        return reason

    
