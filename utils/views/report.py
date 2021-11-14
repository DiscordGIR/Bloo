import discord
from discord import ui
from discord.ext.commands import Context
import pytimeparse
from data.services.guild_service import guild_service
from utils.context import PromptData
from utils.mod.global_modactions import ban, mute, unmute
from utils.permissions.permissions import permissions

class ReportActions(ui.View):
    def __init__(self, author: discord.Member):
        super().__init__()
        self.author = author

    async def start(self, ctx: Context):
        self.ctx = ctx
        await self.wait()
        
    def check(self, interaction: discord.Interaction):
        if not permissions.has(self.author.guild, interaction.user, 5):
            return False
        return True

    @ui.button(emoji="✅", label="Dismiss", style=discord.ButtonStyle.primary)
    async def dismiss(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.message.delete()
        
    @ui.button(emoji="🆔", label="Post ID", style=discord.ButtonStyle.primary)
    async def id(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.channel.send(self.author.id)

    @ui.button(emoji="🧹", label="Clean up", style=discord.ButtonStyle.primary)
    async def purge(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        await self.ctx.channel.purge(limit=100)

class RaidPhraseReportActions(ui.View):
    def __init__(self, author: discord.Member, domain: str):
        super().__init__()
        self.author = author
        self.domain = domain

    async def start(self, ctx: Context):
        self.ctx = ctx
        await self.wait()
        
    def check(self, interaction: discord.Interaction):
        if not permissions.has(self.author.guild, interaction.user, 5):
            return False
        return True

    @ui.button(emoji="✅", label="Dismiss", style=discord.ButtonStyle.primary)
    async def dismiss(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        try:
            await unmute(self.ctx, self.author, reason="Reviewed by a moderator.")
        except Exception:
            await self.ctx.send_warning("I wasn't able to unmute them.", delete_after=5)
        finally:
            await self.ctx.message.delete()
        
    @ui.button(emoji="💀", label="Ban and add raidphrase", style=discord.ButtonStyle.primary)
    async def ban(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        try:
            await ban(self.ctx, self.author, reason="Raid phrase detected")
            self.ctx.bot.ban_cache.ban(self.author.id)
        except Exception:
            await self.ctx.send_warning("I wasn't able to ban them.", delete_after=5)

        done = guild_service.add_raid_phrase(self.domain)
        if done:
            await self.ctx.send_success(f"{self.domain} was added to the raid phrase list.", delete_after=5)
        else:
            await self.ctx.send_warning(f"{self.domain} was already in the raid phrase list.", delete_after=5)

        await self.ctx.message.delete()

class SpamReportActions(ui.View):
    def __init__(self, author: discord.Member):
        super().__init__()
        self.author = author

    async def start(self, ctx: Context):
        self.ctx = ctx
        await self.wait()
        
    def check(self, interaction: discord.Interaction):
        if not permissions.has(self.author.guild, interaction.user, 5):
            return False
        return True

    @ui.button(emoji="✅", label="Dismiss", style=discord.ButtonStyle.primary)
    async def dismiss(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        try:
            await unmute(self.ctx, self.author, reason="Reviewed by a moderator.")
        except:
            await self.ctx.send_warning("I wasn't able to unmute them.", delete_after=5)
        finally:
            await self.ctx.message.delete()
        
    @ui.button(emoji="💀", label="Ban", style=discord.ButtonStyle.primary)
    async def ban(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        try:
            await ban(self.ctx, self.author, reason="Spam detected")
        except Exception:
            await self.ctx.send_warning("I wasn't able to ban them.")
        finally:
            await self.ctx.message.delete()
        
    @ui.button(emoji="⚠️", label="Temporary mute", style=discord.ButtonStyle.primary)
    async def mute(self, button: ui.Button, interaction: discord.Interaction):
        if not self.check(interaction):
            return
        
        prompt_data = PromptData(value_name="duration", 
                                        description="Please enter a duration for the mute (i.e 15m).",
                                        convertor=pytimeparse.parse,
                                        )
        await interaction.response.defer()
        self.ctx.author = interaction.user
        duration = await self.ctx.prompt(prompt_data)
        await mute(self.ctx, self.author, duration, reason="A moderator has reviewed your spam report.")
        await self.ctx.message.delete()
