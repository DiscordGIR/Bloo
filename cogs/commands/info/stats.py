import os
import platform
import traceback
from datetime import datetime
from math import floor

import discord
import psutil
from discord.commands import Option, slash_command
from discord.commands.errors import ApplicationCommandInvokeError
from discord.ext import commands
from discord.utils import format_dt
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.checks import PermissionsFailure, whisper


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Pong!")
    async def ping(self, ctx: BlooContext) -> None:
        embed = discord.Embed(
            title="Pong!", color=discord.Color.blurple())
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
    async def roleinfo(self, ctx: BlooContext, role: Option(discord.Role, description="Role to view info of")) -> None:
        embed = discord.Embed(title="Role Statistics")
        embed.description = f"{len(role.members)} members have role {role.mention}"
        embed.color = role.color
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Statistics about the bot")
    async def stats(self, ctx: BlooContext) -> None:
        process = psutil.Process(os.getpid())

        embed = discord.Embed(
            title=f"{self.bot.user.name} Statistics", color=discord.Color.blurple())
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.add_field(name="Bot started", value=format_dt(self.start_time, style='R'))
        embed.add_field(name="CPU Usage", value=f"{psutil.cpu_percent()}%")
        embed.add_field(name="Memory Usage",
                        value=f"{floor(process.memory_info().rss/1000/1000)} MB")
        embed.add_field(name="Python Version", value=platform.python_version())

        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Displays info about the server")
    async def serverinfo(self, ctx: BlooContext):
        guild = ctx.guild
        embed = discord.Embed(title="Server Information")
        embed.color = discord.Color.blurple()
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

    @ping.error
    @roleinfo.error
    @stats.error
    @serverinfo.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, ApplicationCommandInvokeError):
            error = error.original
        
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error("A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(Stats(bot))
