import discord

def prepare_warn_log(author, user, case):
    """Prepares warn log
    
    Parameters
    ----------
    author : discord.Member
        "Mod who warned the member"
    user : discord.Member
        "Member who was warned"
    case
        "Case object"
        
    """
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
    """Prepares liftwarn log
    
    Parameters
    ----------
    author : discord.Member
        "Mod who lifted the warn"
    user : discord.Member
        "Member who's warn was lifted"
    case
        "Case object"
        
    """
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
    """Prepares log for reason edits
    
    Parameters
    ----------
    author : discord.Member
        "Mod who updated the reason"
    user : discord.Member
        "Member who's case reason was edited"
    case
        "Case object"
    old_reason : str
        "Old case reason"
        
    """
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
    """Prepares log for point removal
    
    Parameters
    ----------
    author : discord.Member
        "Mod who removed the points"
    user : discord.Member
        "Member whose points were removed"
    case
        "Case object"
        
    """
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
    """Prepares ban log
    
    Parameters
    ----------
    author : discord.Member
        "Mod who banned the member"
    user : discord.Member
        "Member who was banned"
    case
        "Case object"
        
    """
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
    """Prepares unban log
    
    Parameters
    ----------
    author : discord.Member
        "Mod who unbanned the member"
    user : discord.Member
        "Member who was unbanned"
    case
        "Case object"
        
    """
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
    """Prepares kick log
    
    Parameters
    ----------
    author : discord.Member
        "Mod who kicked the member"
    user : discord.Member
        "Member who was kicked"
    case
        "Case object"
        
    """
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
    """Prepares mute log
    
    Parameters
    ----------
    author : discord.Member
        "Mod who muted the member"
    user : discord.Member
        "Member who was muted"
    case
        "Case object"
        
    """
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
    """Prepares unmute log
    
    Parameters
    ----------
    author : discord.Member
        "Mod who unmuted the member"
    user : discord.Member
        "Member who was unmuted"
    case
        "Case object"
        
    """
    embed = discord.Embed(title="Member Unmuted")
    embed.color = discord.Color.green()
    embed.set_author(name=user, icon_url=user.display_avatar)
    embed.add_field(name="Member", value=f'{user} ({user.mention})', inline=True)
    embed.add_field(name="Mod", value=f'{author} ({author.mention})', inline=True)
    embed.add_field(name="Reason", value=case.reason, inline=True)
    embed.set_footer(text=f"Case #{case._id} | {user.id}")
    embed.timestamp = case.date
    return embed
