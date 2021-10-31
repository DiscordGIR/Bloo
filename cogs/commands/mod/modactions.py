import traceback
from datetime import datetime, timedelta
from typing import Union

import humanize
import pytimeparse
from data.model.case import Case
from data.model.guild import Guild
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands import Option, slash_command
from discord.ext import commands
from discord.member import Member
from discord.user import User
from discord.utils import escape_markdown, escape_mentions
from utils.checks import PermissionsFailure, mod_and_up, whisper
from utils.config import cfg
from utils.context import BlooContext
from utils.converters import (mods_and_above_external_resolver,
                              mods_and_above_member_resolver, user_resolver)
from utils.mod_logs import prepare_kick_log, prepare_mute_log, prepare_warn_log
from utils.slash_perms import slash_perms

"""
Make sure to add the cog to the initial_extensions list
in main.py
"""

class ModActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @whisper()
    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Warn a user", permissions=slash_perms.mod_and_up())
    async def warn(self, ctx: BlooContext, user: Option(Member, description="User to warn"), points:Option(int, description="Amount of points to warn for"), reason: Option(str, description="Reason for warn", required=False) = "No reason."):
        """Warn a user (mod only)

        Example usage
        --------------
        !warn <@user/ID> <points> <reason (optional)>
        
        Parameters
        ----------
        user : discord.Member
            "The member to warn"
        points : int
            "Number of points to warn far"
        reason : str, optional
            "Reason for warning, by default 'No reason.'"

        """
        user = await mods_and_above_external_resolver(ctx, user)
        
        if points < 1:  # can't warn for negative/0 points
            raise commands.BadArgument(message="Points can't be lower than 1.")

        db_guild = guild_service.get_guild()

        reason = escape_markdown(reason)

        # prepare the case object for database
        case = Case(
            _id=db_guild.case_id,
            _type="WARN",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
            punishment=str(points)
        )

        # increment case ID in database for next available case ID
        guild_service.inc_caseid()
        # add new case to DB
        user_service.add_case(user.id, case)
        # add warnpoints to the user in DB
        user_service.inc_points(user.id, points)

        # fetch latest document about user from DB
        db_user = user_service.get_user(user.id)
        cur_points = db_user.warn_points

        # prepare log embed, send to #public-mod-logs, user, channel where invoked
        log = await prepare_warn_log(ctx.author, user, case)
        log.add_field(name="Current points", value=cur_points, inline=True)

        # also send response in channel where command was called
        dmed = await self.notify_user_warn(ctx, user, db_user, db_guild, cur_points, log)
        await ctx.respond(embed=log, delete_after=10)
        await self.submit_public_log(ctx, db_guild, user, log, dmed)

    @whisper()
    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Kick a user", permissions=slash_perms.mod_and_up())
    async def kick(self, ctx: BlooContext, member: Option(Member, description="User to kick"), *, reason: Option(str, description="Reason for kick", required=False) = "No reason.") -> None:
        """Kick a user (mod only)

        Example usage
        --------------
        !kick <@user/ID> <reason (optional)>

        Parameters
        ----------
        user : discord.Member
            "User to kick"
        reason : str, optional
            "Reason for kick, by default 'No reason.'"

        """

        member = await mods_and_above_member_resolver(ctx, member)

        reason = escape_markdown(reason)
        reason = escape_mentions(reason)
        
        db_guild = guild_service.get_guild()

        log = await self.add_kick_case(ctx, member, reason, db_guild)

        try:
            await member.send(f"You were kicked from {ctx.guild.name}", embed=log)
        except Exception:
            pass

        await member.kick(reason=reason)

        await ctx.respond(embed=log, delete_after=10)
        await self.submit_public_log(ctx, db_guild, member, log)


    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Mute a user", permissions=slash_perms.mod_and_up())
    async def mute(self, ctx: BlooContext, member: Option(Member, description="User to mute"), dur: Option(str, description="Duration for mute", required=False), reason: Option(str, description="Reason for mute", required=False) = "No reason.") -> None:
        """Mute a user (mod only)

        Example usage
        --------------
        !mute <@user/ID> <duration> <reason (optional)>

        Parameters
        ----------
        user : discord.Member
            "Member to mute"
        dur : str
            "Duration of mute (i.e 1h, 10m, 1d)"
        reason : str, optional
            "Reason for mute, by default 'No reason.'"

        """
        member = await mods_and_above_member_resolver(ctx, member)

        reason = escape_markdown(reason)
        reason = escape_mentions(reason)

        now = datetime.now()
        delta = pytimeparse.parse(dur)

        if delta is None:
            if reason == "No reason." and dur == "":
                reason = "No reason."
            elif reason == "No reason.":
                reason = dur
            else:
                reason = f"{dur} {reason}"

        mute_role = guild_service.get_guild().role_mute
        mute_role = ctx.guild.get_role(mute_role)

        if mute_role in member.roles:
            raise commands.BadArgument("This user is already muted.")

        case = Case(
            _id=guild_service.get_guild().case_id,
            _type="MUTE",
            date=now,
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )

        if delta:
            try:
                time = now + timedelta(seconds=delta)
                case.until = time
                case.punishment = humanize.naturaldelta(
                    time - now, minimum_unit="seconds")
                ctx.tasks.schedule_unmute(member.id, time)
            except Exception as e:
                print(e)
                raise commands.BadArgument(
                    "An error occured, this user is probably already muted")
        else:
            case.punishment = "PERMANENT"

        guild_service.inc_caseid()
        user_service.add_case(member.id, case)
        u = user_service.get_user(id=member.id)
        u.is_muted = True
        u.save()

        await member.add_roles(mute_role)

        log = await prepare_mute_log(ctx.author, member, case)
        await ctx.respond(embed=log, delete_after=10)

        log.remove_author()
        log.set_thumbnail(url=member.display_avatar)

        dmed = await self.notify_user(member, f"You have been muted in {ctx.guild.name}", log)
        await self.submit_public_log(ctx, guild_service.get_guild(), member, log, dmed)


    async def add_kick_case(self, ctx: BlooContext, user, reason, db_guild):
        # prepare case for DB
        case = Case(
            _id=db_guild.case_id,
            _type="KICK",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
        )

        # increment max case ID for next case
        guild_service.inc_caseid()
        # add new case to DB
        user_service.add_case(user.id, case)

        return await prepare_kick_log(ctx.author, user, case)
    
    async def notify_user(self, user, text, log):
        try:
            await user.send(text, embed=log)
        except Exception:
            return False
        return True

    async def notify_user_warn(self, ctx: BlooContext, user: User, db_user, db_guild, cur_points: int, log):
        log_kickban = None
        dmed = True
        
        if cur_points >= 600:
            # automatically ban user if more than 600 points
            dmed = await self.notify_user(user, f"You were banned from {ctx.guild.name} for reaching 600 or more points.", log)
            log_kickban = await self.add_ban_case(ctx, user, "600 or more warn points reached.")
            await user.ban(reason="600 or more warn points reached.")

        elif cur_points >= 400 and not db_user.was_warn_kicked and isinstance(user, Member):
            # kick user if >= 400 points and wasn't previously kicked
            user_service.set_warn_kicked(user.id)

            dmed = await self.notify_user(user, f"You were kicked from {ctx.guild.name} for reaching 400 or more points. Please note that you will be banned at 600 points.", log)
            log_kickban = await self.add_kick_case(ctx, user, "400 or more warn points reached.")
            await user.kick(reason="400 or more warn points reached.")

        else:
            if isinstance(user, Member):
                dmed = await self.notify_user(user, f"You were warned in {ctx.guild.name}. Please note that you will be kicked at 400 points and banned at 600 points.", log)

        if log_kickban:
            await self.submit_public_log(ctx, db_guild, user, log_kickban)

        return dmed

    async def submit_public_log(self, ctx: BlooContext, db_guild: Guild, user: Union[Member, User], log, dmed: bool = None):
        public_chan = ctx.guild.get_channel(
            db_guild.channel_public)
        if public_chan:
            log.remove_author()
            log.set_thumbnail(url=user.display_avatar)
            if dmed is not None:
                await public_chan.send(user.mention if not dmed else "", embed=log)
            else:
                await public_chan.send(embed=log)

    # @lock.error
    # @unlock.error
    # @freezeable.error
    # @unfreezeable.error
    # @freeze.error
    # @unfreeze.error
    # @unmute.error
    @mute.error
    # @liftwarn.error
    # @unban.error
    # @ban.error
    @warn.error
    # @purge.error
    @kick.error
    # @roblox.error
    # @editreason.error
    # @removepoints.error
    async def info_error(self,  ctx: BlooContext, error):
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error(error)
            traceback.print_exc()


def setup(bot):
    bot.add_cog(ModActions(bot))
