import discord
from discord import ui
from utils.context import BlooContext, PromptData


class WarnView(ui.View):
    def __init__(self, ctx: BlooContext, member: discord.Member, warn):
        super().__init__(timeout=30)
        self.member = member
        self.warn = warn
        self.ctx = ctx

    async def on_timeout(self) -> None:
        await self.ctx.send_warning("Timed out.")

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

    @ui.button(label="Other...", style=discord.ButtonStyle.primary)
    async def other(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        reason = await self.prompt_reason(interaction)
        if reason and reason is not None:
            await self.warn(self.ctx, self.member, 50, reason)

    @ui.button(emoji="❌", label="cancel", style=discord.ButtonStyle.primary)
    async def cancel(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.send_warning("Cancelled")

    async def prompt_reason(self, interaction: discord.Interaction):
        prompt_data = PromptData(value_name="Reason", 
                                        description="Reason for warn?",
                                        convertor=str,
                                        timeout=30
                                        )
        await interaction.response.defer()
        self.ctx.author = interaction.user
        reason = await self.ctx.prompt(prompt_data)
        return reason

    
