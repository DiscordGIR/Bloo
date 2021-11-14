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

    @ui.button(label="piracy", style=discord.ButtonStyle.primary)
    async def piracy(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        await self.warn(self.ctx, self.member, 50, "piracy")

    @ui.button(label="slurs", style=discord.ButtonStyle.primary)
    async def slurs(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        await self.warn(self.ctx, self.member, 50, "slurs")

    @ui.button(label="filter bypass", style=discord.ButtonStyle.primary)
    async def filter_bypass(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        await self.warn(self.ctx, self.member, 50, "filter bypass")

    @ui.button(label="rule 5", style=discord.ButtonStyle.primary)
    async def rule5(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        await self.warn(self.ctx, self.member, 50, "rule 5")

    @ui.button(emoji="❌", style=discord.ButtonStyle.primary)
    async def cancel(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.send_warning("Cancelled")

    # async def prompt_reason(self, interaction: discord.Interaction):
    #     prompt_data = PromptData(value_name="Reason", 
    #                                     description="Reason for warn?",
    #                                     convertor=str,
    #                                     )
    #     await interaction.response.defer()
    #     self.ctx.author = interaction.user
    #     reason = await self.ctx.prompt(prompt_data)
    #     return reason

    
