from typing import final
import discord
from discord import ui
from utils.context import BlooContext, PromptData
from utils.mod.global_modactions import warn


class WarnView(ui.View):
    def __init__(self, ctx: BlooContext, member: discord.Member):
        super().__init__(timeout=30)
        self.target_member = member
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

        await warn(self.ctx, self.target_member, 50, "piracy")

    @ui.button(label="slurs", style=discord.ButtonStyle.primary)
    async def slurs(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        await warn(self.ctx, self.target_member, 50, "slurs")

    @ui.button(label="filter bypass", style=discord.ButtonStyle.primary)
    async def filter_bypass(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        await warn(self.ctx, self.target_member, 50, "filter bypass")

    @ui.button(label="rule 5", style=discord.ButtonStyle.primary)
    async def rule5(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        await warn(self.ctx, self.target_member, 50, "rule 5")

    @ui.button(label="Other...", style=discord.ButtonStyle.primary)
    async def other(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        reason = await self.prompt_reason(interaction)
        if reason and reason is not None:
            await warn(self.ctx, self.target_member, 50, reason)

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


class WarnViewReport(ui.View):
    def __init__(self, member: discord.Member, mod: discord.Member, report_msg: discord.Message):
        super().__init__(timeout=60)
        self.target_member = member
        self.mod = mod
        self.report_msg = report_msg

    async def start(self, ctx: BlooContext):
        self.ctx = ctx
        await self.wait()

    async def on_timeout(self) -> None:
        await self.cleanup()

    def check(self, interaction: discord.Interaction):
        if self.mod != interaction.user:
            return False
        return True

    @ui.button(label="piracy", style=discord.ButtonStyle.primary)
    async def piracy(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        points = await self.prompt_for_points("piracy", interaction)
        if points is None:
            await self.cleanup()
            return

        await warn(self.ctx, self.target_member, points, "piracy")
        await self.post_cleanup()

    @ui.button(label="slurs", style=discord.ButtonStyle.primary)
    async def slurs(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        points = await self.prompt_for_points("slurs", interaction)
        if points is None:
            await self.cleanup()
            return

        await warn(self.ctx, self.target_member, points, "slurs")
        await self.post_cleanup()

    @ui.button(label="filter bypass", style=discord.ButtonStyle.primary)
    async def filter_bypass(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        points = await self.prompt_for_points("filter bypass", interaction)
        if points is None:
            await self.cleanup()
            return

        await warn(self.ctx, self.target_member, points, "filter bypass")
        await self.post_cleanup()

    @ui.button(label="rule 1", style=discord.ButtonStyle.primary)
    async def rule_one(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        points = await self.prompt_for_points("rule 1", interaction)
        if points is None:
            await self.cleanup()
            return

        await warn(self.ctx, self.target_member, points, "rule 1")
        await self.post_cleanup()

    @ui.button(label="rule 5", style=discord.ButtonStyle.primary)
    async def rule_five(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        points = await self.prompt_for_points("rule 5", interaction)
        if points is None:
            await self.cleanup()
            return

        await warn(self.ctx, self.target_member, points, "rule 5")
        await self.post_cleanup()

    @ui.button(label="Other...", style=discord.ButtonStyle.primary)
    async def other(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        reason = await self.prompt_for_reason(interaction)
        if not reason or reason is None:
            await self.cleanup()
            return

        points = await self.prompt_for_points(reason, interaction)
        if points is None:
            await self.cleanup()
            return

        await warn(self.ctx, self.target_member, points, reason)
        await self.post_cleanup()

    @ui.button(emoji="❌", label="Cancel", style=discord.ButtonStyle.primary)
    async def cancel(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        await self.cleanup()

    async def prompt_for_points(self, reason: str, interaction: discord.Interaction):
        view = PointsView(self.mod)
        temp = await self.ctx.bot.get_application_context(interaction)

        if not temp.interaction.response.is_done():
            await temp.interaction.response.defer()

        await self.ctx.message.edit(embed=discord.Embed(description=f"Warning for `{reason}`. How many points, {self.mod.mention}?", color=discord.Color.blurple()), view=view)
        await view.start(self.ctx.message)

        return view.value

    async def prompt_for_reason(self, interaction: discord.Interaction):
        prompt_data = PromptData(value_name="Reason", 
                                        description="Reason for warn?",
                                        convertor=str,
                                        timeout=30
                                        )
        if not interaction.response.is_done():
            await interaction.response.defer()
        self.ctx.author = interaction.user
        reason = await self.ctx.prompt(prompt_data)
        return reason

    async def cleanup(self):
        try:
            await self.ctx.message.delete()
        except:
            pass
        finally:
            self.stop()

    async def post_cleanup(self):
        try:
            await self.report_msg.delete()
        except:
            pass
        finally:
            self.stop()


class PointsView(ui.View):
    def __init__(self, mod: discord.Member):
        super().__init__(timeout=15)
        self.mod = mod
        self.value = None

    async def start(self, points_msg):
        self.points_msg = points_msg
        await self.wait()

    def check(self, interaction: discord.Interaction):
        if self.mod != interaction.user:
            return False
        return True

    async def on_timeout(self) -> None:
        try:
            await self.points_msg.delete()
        except:
            pass

    @ui.button(label="50 points", style=discord.ButtonStyle.primary)
    async def fiddy(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        self.value = 50
        await self.points_msg.delete()
        self.stop()

    @ui.button(label="100 points", style=discord.ButtonStyle.primary)
    async def hunnit(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        self.value = 100
        await self.points_msg.delete()
        self.stop()

    @ui.button(label="150 points", style=discord.ButtonStyle.primary)
    async def hunnitfiddy(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        self.value = 150
        await self.points_msg.delete()
        self.stop()

    @ui.button(label="200 points", style=discord.ButtonStyle.primary)
    async def twohunnit(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return

        self.value = 200
        await self.points_msg.delete()
        self.stop()
