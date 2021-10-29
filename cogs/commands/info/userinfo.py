import traceback
from datetime import datetime

from math import floor

from data.services.user_service import user_service
from discord.colour import Color
from discord.commands import slash_command
from discord.commands.commands import Option
from discord.embeds import Embed
from discord.ext import commands
from discord.member import Member
from discord.utils import format_dt
from utils.checks import PermissionsFailure, whisper
from utils.config import cfg
from utils.context import GIRContext
from utils.permissions import permissions


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get avatar of another user or yourself.")
    async def avatar(self, ctx: GIRContext, user: Option(Member, description="User to get avatar of", required=False)) -> None:
        if not user:
            user = ctx.user
        embed = Embed(title=f"{user}'s Avatar", color=Color.random())
        embed.set_image(url=user.avatar)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info of another user or yourself.")
    async def userinfo(self, ctx: GIRContext, user: Option(Member, description="User to get info of", required=False)) -> None:
        # TODO when pycord fixes this behavior: handle external members

        if user:
            if not permissions.has(ctx.guild, ctx.author, 6):
                raise PermissionsFailure(
                    "You do not have permission to access another user's userinfo.")
        else:
            user = ctx.user

        roles = ""
        reversed_roles = user.roles
        reversed_roles.reverse()
        for role in reversed_roles[:-1]:
            roles += role.mention + " "

        results = user_service.get_user(user.id)

        embed = Embed(title=f"User Information", color=user.color)
        embed.set_author(name=user)
        embed.set_thumbnail(url=user.avatar)
        embed.add_field(name="Username",
                        value=f'{user} ({user.mention})', inline=True)
        embed.add_field(
            name="Level", value=results.level if not results.is_clem else "0", inline=True)
        embed.add_field(
            name="XP", value=results.xp if not results.is_clem else "0/0", inline=True)
        embed.add_field(
            name="Roles", value=roles if roles else "None", inline=False)
        embed.add_field(
            name="Join date", value=f"{format_dt(user.joined_at, style='F')} ({format_dt(user.joined_at, style='R')})", inline=True)
        embed.add_field(name="Account creation date",
                        value=f"{format_dt(user.created_at, style='F')} ({format_dt(user.created_at, style='R')})", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Show your or another user's XP")
    async def xp(self, ctx: GIRContext, user: Option(Member, description="Member to show xp of", required=False)):
        """Show your or another user's XP

        Example usage
        --------------
        !xp <@user/ID (optional)

        Parameters
        ----------
        user : discord.Member, optional
            "User to get XP of, by default None"

        """

        if user is None:
            user = ctx.author

        results = user_service.get_user(user.id)

        embed = Embed(title="Level Statistics")
        embed.color = user.top_role.color
        embed.set_author(name=user, icon_url=user.avatar)
        embed.add_field(
            name="Level", value=results.level if not results.is_clem else "0", inline=True)
        embed.add_field(
            name="XP", value=f'{results.xp}/{xp_for_next_level(results.level)}' if not results.is_clem else "0/0", inline=True)
        rank, overall = user_service.leaderboard_rank(results.xp)
        embed.add_field(
            name="Rank", value=f"{rank}/{overall}" if not results.is_clem else f"{overall}/{overall}", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Show your or another user's warnpoints")
    async def warnpoints(self, ctx: GIRContext, user: Option(Member, description="Member to show warnpoints of", required=False)):
        """Show a user's warnpoints (mod only)

        Example usage
        --------------
        !warnpoints <@user/ID>

        Parameters
        ----------
        user : discord.Member
            "User whose warnpoints to show"

        """

        # if an invokee is not provided in command, call command on the invoker
        # (get invoker's warnpoints)
        user = user or ctx.author

        # users can only invoke on themselves if they aren't mods
        if not permissions.has(ctx.guild, ctx.author, 5) and user.id != ctx.author.id:
            raise PermissionsFailure(
                f"You don't have permissions to check others' warnpoints.")

        # fetch user profile from database
        results = user_service.get_user(user.id)

        embed = Embed(title="Warn Points")
        embed.color = Color.orange()
        embed.set_thumbnail(url=user.avatar)
        embed.add_field(
            name="Member", value=f'{user.mention}\n{user}\n({user.id})', inline=True)
        embed.add_field(name="Warn Points",
                        value=results.warn_points, inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    # @cases.error
    @userinfo.error
    @warnpoints.error
    @xp.error
    # @xptop.error
    async def info_error(self, ctx: GIRContext, error):
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error("A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def xp_for_next_level(_next):
    """Magic formula to determine XP thresholds for levels
    """

    level = 0
    xp = 0

    for _ in range(0, _next):
        xp = xp + 45 * level * (floor(level / 10) + 1)
        level += 1

    return xp


def setup(bot):
    bot.add_cog(UserInfo(bot))
