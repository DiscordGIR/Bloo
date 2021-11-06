import discord
from services import guild_service, user_service
from discord.utils import format_dt
from utils.views import ReportActions


async def report(bot: discord.Client, message: discord.Message, word: str, invite=None):
    db_guild = guild_service.get_guild()
    channel = message.guild.get_channel(db_guild.channel_reports)

    # ping_string = prepare_ping_string(db_guild, message)
    ping_string = ""
    view = ReportActions(message.author)

    if invite:
        embed = prepare_embed(message, word, title="Invite filter")
        report_msg = await channel.send(f"{ping_string}\nMessage contained invite: {invite}", embed=embed, view=view)
    else:
        embed = prepare_embed(message, word)
        report_msg = await channel.send(ping_string, embed=embed, view=view)

    ctx = await bot.get_context(report_msg)
    await view.start(ctx)


def prepare_ping_string(db_guild, message):
    ping_string = ""
    role = message.guild.get_role(db_guild.role_moderator)
    for member in role.members:
        offline_ping = (user_service.get_user(member.id)).offline_report_ping
        if member.status == discord.Status.online or offline_ping:
            ping_string += f"{member.mention} "

    return ping_string


def prepare_embed(message: discord.Message, word: str = None, title="Word filter"):
    member = message.author
    user_info = user_service.get_user(member.id)
    joined = member.joined_at.strftime("%B %d, %Y, %I:%M %p")
    created = member.created_at.strftime("%B %d, %Y, %I:%M %p")
    rd = user_service.rundown(member.id)
    rd_text = ""
    for r in rd:
        if r._type == "WARN":
            r.punishment += " points"
        rd_text += f"**{r._type}** - {r.punishment} - {r.reason} - {format_dt(r.date, style='R')}\n"

    embed = discord.Embed(title=title)
    embed.color = discord.Color.red()

    embed.set_thumbnail(url=member.display_avatar)
    embed.add_field(name="Member", value=f"{member} ({member.mention})")
    embed.add_field(name="Channel", value=message.channel.mention)

    if len(message.content) > 400:
        message.content = message.content[0:400] + "..."

    if word is not None:
        embed.add_field(name="Message", value=discord.utils.escape_markdown(
            message.content) + f"\n\n[Link to message]({message.jump_url}) | Filtered word: **{word}**", inline=False)
    else:
        embed.add_field(name="Message", value=discord.utils.escape_markdown(
            message.content) + f"\n\n[Link to message]({message.jump_url})", inline=False)
    embed.add_field(
        name="Join date", value=f"{format_dt(member.joined_at, style='F')} ({format_dt(member.joined_at, style='R')})", inline=True)
    embed.add_field(name="Created",
                    value=f"{format_dt(member.created_at, style='F')} ({format_dt(member.created_at, style='R')})", inline=True)

    embed.add_field(name="Warn points",
                    value=user_info.warn_points, inline=True)

    reversed_roles = member.roles
    reversed_roles.reverse()

    roles = ""
    for role in reversed_roles[0:4]:
        if role != member.guild.default_role:
            roles += role.mention + " "
    roles = roles.strip() + "..."

    embed.add_field(
        name="Roles", value=roles if roles else "None", inline=False)

    if len(rd) > 0:
        embed.add_field(name=f"{len(rd)} most recent cases",
                        value=rd_text, inline=True)
    else:
        embed.add_field(name=f"Recent cases",
                        value="This user has no cases.", inline=True)
    return embed
