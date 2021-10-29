import os
import platform
from datetime import datetime
from math import floor
from discord.utils import format_dt

import psutil
from discord.colour import Color
from discord.commands import slash_command
from discord.commands.commands import Option
from discord.embeds import Embed
from discord.ext import commands
from discord.role import Role
from utils.checks import whisper
from utils.config import cfg
from utils.context import GIRContext


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Pong!")
    async def ping(self, ctx: GIRContext) -> None:
        embed = Embed(
            title="Pong!", color=Color.blurple())
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.description = "Latency: testing..."

        # measure time between sending a message and time it is posted
        b = datetime.utcnow()
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)
       
        ping = floor((datetime.utcnow() - b).total_seconds() * 1000)
        embed.description = ""
        embed.add_field(name="Message Latency", value=f"`{ping}ms`")
        embed.add_field(name="API Latency", value=f"`{floor(self.bot.latency*1000)}ms`")
        await ctx.edit(embed=embed)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get number of users of a role")
    async def roleinfo(self, ctx: GIRContext, role: Option(Role, description="Role to view info of")) -> None:
        embed = Embed(title="Role Statistics")
        embed.description = f"{len(role.members)} members have role {role.mention}"
        embed.color = role.color
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Statistics about the bot")
    async def stats(self, ctx: GIRContext) -> None:
        process = psutil.Process(os.getpid())

        embed = Embed(
            title=f"{self.bot.user.name} Statistics", color=Color.blurple())
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.add_field(name="Bot started", value=format_dt(self.start_time, style='R'))
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%")
        embed.add_field(name="Memory Usage",
                        value=f"{floor(process.memory_info().rss/1000/1000)} MB")
        embed.add_field(name="Python Version", value=platform.python_version())

        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Displays info about the server")
    async def serverinfo(self, ctx: GIRContext):
        guild = ctx.guild
        embed = Embed(title="Server Information")
        embed.color = Color.blurple()
        embed.set_thumbnail(url=guild.icon)
        embed.add_field(name="Region", value=guild.region, inline=True)
        embed.add_field(name="Boost Tier",
                        value=guild.premium_tier, inline=True)
        embed.add_field(name="Users", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(
            guild.channels) + len(guild.voice_channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Created", value=f"{format_dt(guild.created_at, style='F')} ({format_dt(guild.created_at, style='R')})", inline=True)

        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)


def setup(bot):
    bot.add_cog(Stats(bot))
