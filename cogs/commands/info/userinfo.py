import discord
from discord.commands import errors, slash_command, Option, message_command, user_command
from discord.utils import format_dt
from discord.ext import commands
import traceback
from datetime import datetime
from math import floor
from typing import Union
from data.services.user_service import user_service
from utils.menu import Menu
from utils.permissions.checks import PermissionsFailure, whisper
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.converters  import user_resolver
from utils.permissions.permissions import permissions

async def format_xptop_page(entry, all_pages, current_page, ctx):
    embed = discord.Embed(title=f'Leaderboard', color=discord.Color.blurple())
    for i, user in entry:
        member = ctx.guild.get_member(user._id)
        trophy = ''
        if current_page == 1:
            if i == entry[0][0]:
                trophy = ':first_place:'
                embed.set_thumbnail(url=member.avatar)
            if i == entry[1][0]:
                trophy = ':second_place:'
            if i == entry[2][0]:
                trophy = ':third_place:'
            
            
        embed.add_field(name=f"#{i+1} - Level {user.level}", value=f"{trophy} {member.mention}", inline=False)
            
    embed.set_footer(text=f"Page {current_page} of {len(all_pages)}")
    return embed

async def format_cases_page(entry, all_pages, current_page, ctx):
    page_count = 0
    pun_map = {
        "KICK": "Kicked",
        "BAN": "Banned",
        "CLEM": "Clemmed",
        "UNBAN": "Unbanned",
        "MUTE": "Duration",
        "REMOVEPOINTS": "Points removed"
    }
    user = ctx.case_user
    u = user_service.get_user(user.id)
    
    for page in all_pages:
        for case in page:
            page_count = page_count + 1
    embed = discord.Embed(title=f'Cases - {u.warn_points} warn points', color=discord.Color.blurple())
    embed.set_author(name=user, icon_url=user.avatar)
    for case in entry:
        timestamp = case.date
        formatted = f"{format_dt(timestamp, style='F')} ({format_dt(timestamp, style='R')})"
        if case._type == "WARN" or case._type == "LIFTWARN":
            if case.lifted:
                embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id} [LIFTED]', value=f'**Points**: {case.punishment}\n**Reason**: {case.reason}\n**Lifted by**: {case.lifted_by_tag}\n**Lift reason**: {case.lifted_reason}\n**Warned on**: {formatted}', inline=True)
            elif case._type == "LIFTWARN":
                embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id} [LIFTED (legacy)]', value=f'**Points**: {case.punishment}\n**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Warned on**: {formatted}', inline=True)
            else:
                embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id}', value=f'**Points**: {case.punishment}\n**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Warned on**: {formatted}', inline=True)
        elif case._type == "MUTE" or case._type == "REMOVEPOINTS":
                embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id}', value=f'**{pun_map[case._type]}**: {case.punishment}\n**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Time**: {formatted}', inline=True)
        elif case._type in pun_map:
            embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id}', value=f'**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**{pun_map[case._type]} on**: {formatted}', inline=True)
        else:
            embed.add_field(name=f'{await determine_emoji(case._type)} Case #{case._id}', value=f'**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Time**: {formatted}', inline=True)
    embed.set_footer(text=f"Page {current_page} of {len(all_pages)} - newest cases first ({page_count} total cases)")
    return embed

async def determine_emoji(type):
    emoji_dict = {
        "KICK": "👢",
        "BAN": "❌",
        "UNBAN": "✅",
        "MUTE": "🔇",
        "WARN": "⚠️",
        "UNMUTE": "🔈",
        "LIFTWARN": "⚠️",
        "REMOVEPOINTS": "⬇️",
        "CLEM": "👎"
    }
    return emoji_dict[type]


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get avatar of another user or yourself.")
    async def avatar(self, ctx: BlooContext, user: Option(discord.Member, description="User to get avatar of", required=False)) -> None:
        if not user:
            user = ctx.user
        embed = discord.Embed(title=f"{user}'s Avatar", color=discord.Color.random())
        embed.set_image(url=user.avatar)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info of another user or yourself.")
    async def userinfo(self, ctx: BlooContext, user: Option(discord.Member, description="User to get info of", required=False)) -> None:
        await self.handle_userinfo(ctx, user)
    
    @whisper()
    @user_command(guild_ids=[cfg.guild_id], name="Userinfo")
    async def userinfo_rc(self, ctx: BlooContext, user: discord.Member) -> None:
        await self.handle_userinfo(ctx, user)
    
    @whisper()
    @message_command(guild_ids=[cfg.guild_id], name="Userinfo")
    async def userinfo_msg(self, ctx: BlooContext, message: discord.Message) -> None:
        await self.handle_userinfo(ctx, message.author)

    async def handle_userinfo(self, ctx: BlooContext, user: Union[discord.User, discord.Member]):
        is_mod = permissions.has(ctx.guild, ctx.author, 5)
        if user is None:
            user = ctx.author
        elif isinstance(user, str) or isinstance(user, int):
            user = await user_resolver(ctx, user)

        # is the invokee in the guild?
        if isinstance(user, discord.User) and not is_mod:
            raise commands.BadArgument("You do not have permission to use this command.")

        # non-mods are only allowed to request their own userinfo
        if not is_mod and user.id != ctx.author.id:
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        # prepare list of roles and join date
        roles = ""
        if isinstance(user, discord.Member) and user.joined_at is not None:
            reversed_roles = user.roles
            reversed_roles.reverse()

            for role in reversed_roles[:-1]:
                roles += role.mention + " "
            joined = f"{format_dt(user.joined_at, style='F')} ({format_dt(user.joined_at, style='R')})"
        else:
            roles = "No roles."
            joined = f"User not in {ctx.guild}"

        results = user_service.get_user(user.id)

        embed = discord.Embed(title=f"User Information", color=user.color)
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
            name="Join date", value=joined, inline=True)
        embed.add_field(name="Account creation date",
                        value=f"{format_dt(user.created_at, style='F')} ({format_dt(user.created_at, style='R')})", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Show your or another user's XP")
    async def xp(self, ctx: BlooContext, user: Option(discord.Member, description="Member to show xp of", required=False)):
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

        embed = discord.Embed(title="Level Statistics")
        embed.color = user.top_role.color
        embed.set_author(name=user, icon_url=user.display_avatar)
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
    async def warnpoints(self, ctx: BlooContext, user: Option(discord.Member, description="Member to show warnpoints of", required=False)):
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

        embed = discord.Embed(title="Warn Points", color=discord.Color.orange())
        embed.set_thumbnail(url=user.avatar)
        embed.add_field(
            name="Member", value=f'{user.mention}\n{user}\n({user.id})', inline=True)
        embed.add_field(name="Warn Points",
                        value=results.warn_points, inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.respond(embed=embed, ephemeral=ctx.whisper)
    
    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Show the XP leaderboard.")
    async def xptop(self, ctx: BlooContext):
        """Show XP leaderboard for top 100, ranked highest to lowest.
        Example usage
        --------------
        !xptop
        """

        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        results = enumerate(user_service.leaderboard())
        results = [ (i, m) for (i, m) in results if ctx.guild.get_member(m._id) is not None][0:100]
        menu = Menu(list(chunks(results, 10)), ctx.channel, format_xptop_page, True, ctx, True)
        await menu.init_menu()
    
    @slash_command(guild_ids=[cfg.guild_id], description="Show your or another user's cases")
    async def cases(self, ctx: BlooContext, user: Option(discord.Member, description="Member to show cases of", required=False)):
        """Show list of cases of a user (mod only)
        Example usage
        --------------
        !cases <@user/ID>
        Parameters
        ----------
        user : typing.Union[discord.Member,int]
            "User we want to get cases of, doesn't have to be in guild"
        """
        
        # if an invokee is not provided in command, call command on the invoker
        # (get invoker's cases)
        user = user or ctx.author

        # users can only invoke on themselves if they aren't mods
        if not permissions.has(ctx.guild, ctx.author, 5) and user.id != ctx.author.id:
            raise PermissionsFailure(
                f"You don't have permissions to check others' warnpoints.")

        # if user not in guild, fetch their profile from the Discord API
        if isinstance(user, int):
            try:
                user_1 = await self.bot.fetch_user(user)
            except Exception:
                return await ctx.send_error(f"Couldn't find user with ID {user}")
            user = user_1

        # fetch user's cases from our database
        results = user_service.get_cases(user.id)
        if len(results.cases) == 0:
            if isinstance(user, int):
                return await ctx.send_error(f'User with ID {user.id} had no cases.')
            else:
                return await ctx.send_error(f'{user.mention} had no cases.')
        
        # filter out unmute cases because they are irrelevant
        cases = [case for case in results.cases if case._type != "UNMUTE"]
        # reverse so newest cases are first
        cases.reverse()

        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        ctx.case_user = user

        menu = Menu(list(chunks(cases, 10)), ctx.channel, format_cases_page, True, ctx, True)
        await menu.init_menu()

    @cases.error
    @userinfo_rc.error
    @userinfo_msg.error
    @userinfo.error
    @warnpoints.error
    @xp.error
    @xptop.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, errors.ApplicationCommandInvokeError):
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
