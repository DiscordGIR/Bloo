import discord

def prepare_warn_log(author, user, case):
    embed = discord.Embed(title="Member Warned")
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.color = discord.Color.orange()
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Increase", value=case.punishment, inline=True)
    embed.add_field(name="Reason", value=case.reason, inline=True)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed


def prepare_liftwarn_log(author, user, case):
    embed = discord.Embed(title="Member Warn Lifted")
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.color = discord.Color.blurple()
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Decrease", value=case.punishment, inline=True)
    embed.add_field(name="Reason", value=case.lifted_reason, inline=True)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.lifted_date
    return embed

def prepare_editreason_log(author, user, case, old_reason):
    embed = discord.Embed(title="Member Case Updated")
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.color = discord.Color.blurple()
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Old reason", value=old_reason, inline=False)
    embed.add_field(name="New Reason", value=case.reason, inline=False)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed


def prepare_removepoints_log(author, user, case):
    embed = discord.Embed(title="Member Points Removed")
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.color = discord.Color.blurple()
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Decrease", value=case.punishment, inline=True)
    embed.add_field(name="Reason", value=case.reason, inline=True)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed


def prepare_ban_log(author, user, case):
    embed = discord.Embed(title="Member Banned")
    embed.color = discord.Color.blue()
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Reason", value=case.reason, inline=True)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed


def prepare_unban_log(author, user, case):
    embed = discord.Embed(title="Member Unbanned")
    embed.color = discord.Color.blurple()
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.add_field(name="Member", value=f'{user} ({user.id})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Reason", value=case.reason, inline=True)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed


def prepare_kick_log(author, user, case):
    embed = discord.Embed(title="Member Kicked")
    embed.color = discord.Color.green()
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Reason", value=case.reason, inline=False)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed


def prepare_mute_log(author, user, case):
    embed = discord.Embed(title="Member Muted")
    embed.color = discord.Color.red()
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Duration", value=case.punishment, inline=True)
    embed.add_field(name="Reason", value=case.reason, inline=True)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed


def prepare_unmute_log(author, user, case):
    embed = discord.Embed(title="Member Unmuted")
    embed.color = discord.Color.green()
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Reason", value=case.reason, inline=True)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed
