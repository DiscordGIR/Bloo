import discord
from discord.ext import commands
import humanize
from datetime import datetime, timedelta
from data.model.case import Case
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from utils.mod.mod_logs import prepare_mute_log, prepare_unmute_log
from utils.mod.modactions_helpers import add_ban_case, notify_user, submit_public_log

async def mute(ctx, member, dur_seconds = None, reason = "No reason."):
    """Mutes a member
    
    Parameters
    ----------
    ctx : BlooContext
        "Bot context"
    member : discord.Member
        "Member to mute"
    dur_seconds : int
        "Mute duration in settings"
    reason : str
        "Reason for mute"
    
    """
    mute_role = guild_service.get_guild().role_mute
    mute_role = ctx.guild.get_role(mute_role)

    now = datetime.now()

    db_guild = guild_service.get_guild()
    case = Case(
        _id=db_guild.case_id,
        _type="MUTE",
        date=now,
        mod_id=ctx.author.id,
        mod_tag=str(ctx.author),
        reason=reason,
    )

    if dur_seconds:
        try:
            time = now + timedelta(seconds=dur_seconds)
            case.until = time
            case.punishment = humanize.naturaldelta(
                time - now, minimum_unit="seconds")
            ctx.bot.tasks.schedule_unmute(member.id, time)
        except Exception:
            return
    else:
        case.punishment = "PERMANENT"

    guild_service.inc_caseid()
    user_service.add_case(member.id, case)
    u = user_service.get_user(id=member.id)
    u.is_muted = True
    u.save()
    await member.add_roles(mute_role)

    log = prepare_mute_log(ctx.author, member, case)
    await ctx.send(embed=log, delete_after=10)

    log.remove_author()
    log.set_thumbnail(url=member.display_avatar)

    dmed = await notify_user(member, f"You have been muted in {ctx.guild.name}", log)
    await submit_public_log(ctx, db_guild, member, log, dmed)

async def unmute(ctx, member, reason: str = "No reason.") -> None:
    """Unmutes a user (mod only)

    Example usage
    --------------
    /unmute member:<member> reason:<reason>

    Parameters
    ----------
    user : discord.Member
        "Member to unmute"
    reason : str, optional
        "Reason for unmute, by default 'No reason.'"
        
    """

    db_guild = guild_service.get_guild()
    mute_role = db_guild.role_mute
    mute_role = ctx.guild.get_role(mute_role)
    await member.remove_roles(mute_role)

    u = user_service.get_user(id=member.id)
    u.is_muted = False
    u.save()

    try:
        ctx.tasks.cancel_unmute(member.id)
    except Exception:
        pass

    case = Case(
        _id=db_guild.case_id,
        _type="UNMUTE",
        mod_id=ctx.author.id,
        mod_tag=str(ctx.author),
        reason=reason,
    )
    guild_service.inc_caseid()
    user_service.add_case(member.id, case)

    log = prepare_unmute_log(ctx.author, member, case)

    await ctx.send(embed=log, delete_after=10)

    dmed = await notify_user(member, f"You have been unmuted in {ctx.guild.name}", log)
    await submit_public_log(ctx, db_guild, member, log, dmed)
        
async def ban(ctx, user, reason = "No reason."):
    """Bans a user (mod only)

    Example usage
    --------------
    /ban user:<user> reason:<reason>

    Parameters
    ----------
    user : discord.Member
        "The user to be banned, doesn't have to be part of the guild"
    reason : str, optional
        "Reason for ban, by default 'No reason.'"
        
    """

    db_guild = guild_service.get_guild()

    member_is_external = isinstance(user, discord.User)

    log = await add_ban_case(ctx, user, reason, db_guild)

    if not member_is_external:
        await notify_user(user, f"You have been banned from {ctx.guild.name}", log)
        await user.ban(reason=reason)
    else:
        # hackban for user not currently in guild
        await ctx.guild.ban(discord.Object(id=user.id))

    ctx.bot.ban_cache.ban(user.id)
    await ctx.send(embed=log, delete_after=10)
    await submit_public_log(ctx, db_guild, user, log)