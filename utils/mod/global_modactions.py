from datetime import datetime, timedelta

import humanize
from data.model import Case
from data.services import guild_service, user_service
from utils.mod.mod_logs import prepare_mute_log
from utils.mod.modactions_helpers import notify_user, submit_public_log

async def mute(ctx, member, dur_seconds, reason):
    mute_role = guild_service.get_guild().role_mute
    mute_role = ctx.guild.get_role(mute_role)

    if mute_role in member.roles:
        return

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

    if dur_seconds != 0:
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
