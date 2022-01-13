import discord

from typing import Union
from data.model.case import Case
from data.model.guild import Guild
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from utils.context import BlooContext
from utils.mod.mod_logs import prepare_ban_log, prepare_kick_log


async def add_kick_case(ctx: BlooContext, user, reason, db_guild):
    """Adds kick case to user

    Parameters
    ----------
    ctx : BlooContext
        "Bot context"
    user : discord.Member
        "Member who was kicked"
    reason : str
        "Reason member was kicked"
    db_guild
        "Guild DB"

    """
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

    return prepare_kick_log(ctx.author, user, case)


async def notify_user(user, text, log):
    """Notifies a specified user about something

    Parameters
    ----------
    user : discord.Member
        "User to notify"
    text : str
        "Text to send"
    log : discord.Embed
        "Embed to send"
    """
    try:
        await user.send(text, embed=log)
    except Exception:
        return False
    return True


async def notify_user_warn(ctx: BlooContext, user: discord.User, db_user, db_guild, cur_points: int, log):
    """Notifies a specified user about a warn

    Parameters
    ----------
    ctx : BlooContext
        "Bot context"
    user : discord.Member
        "User to notify"
    db_user
        "User DB"
    db_guild
        "Guild DB"
    cur_points : int
        "Number of points the user currently has"
    log : discord.Embed
        "Embed to send"
    """
    log_kickban = None
    dmed = True

    if cur_points >= 600:
        # automatically ban user if more than 600 points
        dmed = await notify_user(user, f"You were banned from {ctx.guild.name} for reaching 600 or more points.", log)
        log_kickban = await add_ban_case(ctx, user, "600 or more warn points reached.", db_guild)
        await user.ban(reason="600 or more warn points reached.")
        ctx.bot.ban_cache.ban(user.id)
    elif cur_points >= 400 and not db_user.was_warn_kicked and isinstance(user, discord.Member):
        # kick user if >= 400 points and wasn't previously kicked
        user_service.set_warn_kicked(user.id)

        dmed = await notify_user(user, f"You were kicked from {ctx.guild.name} for reaching 400 or more points. Please note that you will be banned at 600 points.", log)
        log_kickban = await add_kick_case(ctx, user, "400 or more warn points reached.", db_guild)
        await user.kick(reason="400 or more warn points reached.")
    else:
        if isinstance(user, discord.Member):
            dmed = await notify_user(user, f"You were warned in {ctx.guild.name}. Please note that you will be kicked at 400 points and banned at 600 points.", log)

    if log_kickban:
        await submit_public_log(ctx, db_guild, user, log_kickban)

    return dmed


async def submit_public_log(ctx: BlooContext, db_guild: Guild, user: Union[discord.Member, discord.User], log, dmed: bool = None):
    """Submits a public log

    Parameters
    ----------
    ctx : BlooContext
        "Bot context"
    user : discord.Member
        "User to notify"
    db_user
        "User DB"
    db_guild
        "Guild DB"
    cur_points : int
        "Number of points the user currently has"
    log : discord.Embed
        "Embed to send"
    """
    public_chan = ctx.guild.get_channel(
        db_guild.channel_public)
    if public_chan:
        log.remove_author()
        log.set_thumbnail(url=user.display_avatar)
        if dmed is not None:
            await public_chan.send(user.mention if not dmed else "", embed=log)
        else:
            await public_chan.send(embed=log)


async def add_ban_case(ctx: BlooContext, user: discord.User, reason, db_guild: Guild = None):
    """Adds ban case to user

    Parameters
    ----------
    ctx : BlooContext
        "Bot context"
    user : discord.Member
        "Member who was banned"
    reason : str
        "Reason member was banned"
    db_guild
        "Guild DB"

    """
    # prepare the case to store in DB
    case = Case(
        _id=db_guild.case_id,
        _type="BAN",
        mod_id=ctx.author.id,
        mod_tag=str(ctx.author),
        punishment="PERMANENT",
        reason=reason,
    )

    # increment DB's max case ID for next case
    guild_service.inc_caseid()
    # add case to db
    user_service.add_case(user.id, case)
    # prepare log embed to send to #public-mod-logs, user and context
    return prepare_ban_log(ctx.author, user, case)
