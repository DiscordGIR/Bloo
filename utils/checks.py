from discord.errors import NotFound
from discord.ext import commands
from discord.member import Member
from data.services.guild_service import guild_service
from utils.context import BlooContext

from utils.database import db
from utils.permissions import permissions


class PermissionsFailure(commands.BadArgument):
    def __init__(self, message):
        super().__init__(message)


def always_whisper():
    """Always respond ephemerally
    """
    async def predicate(ctx: BlooContext):
        ctx.whisper = True
        return True
    return commands.check(predicate)


def whisper():
    """If the user is not a moderator and the invoked channel is not #bot-commands, send the response to the command ephemerally
    """
    async def predicate(ctx: BlooContext):
        bot_chan = guild_service.get_guild()
        if not permissions.has(ctx.guild, ctx.author, 5) and ctx.channel.id != bot_chan:
            ctx.whisper = True
        else:
            ctx.whisper = False
        return True
    return commands.check(predicate)


class ModsAndAboveMember(commands.Converter):
    async def convert(self,  ctx: BlooContext, argument):
        user = await commands.MemberConverter().convert(ctx, argument)
        await check_invokee(ctx, user)
        return user

class ModsAndAboveExternal(commands.Converter):
    async def convert(self,  ctx: BlooContext, argument):
        try:
            user = await commands.MemberConverter().convert(ctx, argument)
        except PermissionsFailure as e:
            raise e   
        except Exception:
            try:
                argument = int(argument)
                user = await ctx.bot.fetch_user(argument)
            except Exception:
                raise PermissionsFailure("Could not parse argument \"user\".")
            except NotFound:
                raise PermissionsFailure(
                    f"Couldn't find user with ID {argument}")
            
        await check_invokee(ctx, user)
        return user 

async def check_invokee(ctx, user):
    if isinstance(user, Member):
        if user.id == ctx.author.id:
            await ctx.message.add_reaction("🤔")
            raise PermissionsFailure("You can't call that on yourself.")
        
        if user.id == ctx.bot.user.id:
            await ctx.message.add_reaction("🤔")
            raise PermissionsFailure("You can't call that on me :(")
        
        if user:
                if isinstance(user, Member):
                    if user.top_role >= ctx.author.top_role:
                        raise PermissionsFailure(
                            message=f"{user.mention}'s top role is the same or higher than yours!")


### 

def memplus_and_up():
    async def predicate(ctx: BlooContext):
        if not permissions.has(ctx.guild, ctx.author, 1):
            raise PermissionsFailure("You do not have permission to use this command.")
        
        return True
    return commands.check(predicate)

def mempro_and_up():
    async def predicate(ctx: BlooContext):
        if not permissions.has(ctx.guild, ctx.author, 2):
            raise PermissionsFailure("You do not have permission to use this command.")
        
        return True
    return commands.check(predicate)

def memed_and_up():
    async def predicate(ctx: BlooContext):
        if not permissions.has(ctx.guild, ctx.author, 3):
            raise PermissionsFailure("You do not have permission to use this command.")
        
        return True
    return commands.check(predicate)

def genius_and_up():
    async def predicate(ctx: BlooContext):
        if not permissions.has(ctx.guild, ctx.author, 4):
            raise PermissionsFailure("You do not have permission to use this command.")
        
        return True
    return commands.check(predicate)

####################
# Staff Roles
####################

def submod_or_admin_and_up():
    async def predicate(ctx: BlooContext):
        db = guild_service.get_guild()
        submod = ctx.guild.get_role(db.role_sub_mod)
        if not submod:
            return

        if not (permissions.has(ctx.guild, ctx.author, 6) or submod in ctx.author.roles):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        return True
    return commands.check(predicate)

def genius_or_submod_and_up():
    async def predicate(ctx: BlooContext):
        db = guild_service.get_guild()
        submod = ctx.guild.get_role(db.role_sub_mod)
        if not submod:
            return

        if not (permissions.has(ctx.guild, ctx.author, 4) or submod in ctx.author.roles):
            raise commands.BadArgument(
                "You do not have permission to use this command.")

        return True
    return commands.check(predicate)

def mod_and_up():
    async def predicate(ctx: BlooContext):
        if not permissions.has(ctx.guild, ctx.author, 5):
            raise PermissionsFailure(
                "You do not have permission to use this command.")
        
        return True
    return commands.check(predicate)

def admin_and_up():
    async def predicate(ctx: BlooContext):
        if not permissions.has(ctx.guild, ctx.author, 6):
            raise PermissionsFailure(
                "You do not have permission to use this command.")
        
        return True
    return commands.check(predicate)

####################
# Other
####################

def guild_owner_and_up():
    async def predicate(ctx: BlooContext):
        if not permissions.has(ctx.guild, ctx.author, 7):
            raise PermissionsFailure(
                "You do not have permission to use this command.")
        
        return True
    return commands.check(predicate)

def bot_owner_and_up():
    async def predicate(ctx: BlooContext):
        if not permissions.has(ctx.guild, ctx.author, 9):
            raise PermissionsFailure(
                "You do not have permission to use this command.")
        
        return True
    return commands.check(predicate)

def ensure_invokee_role_lower_than_bot():
    async def predicate(ctx: BlooContext):
        if ctx.me.top_role < ctx.author.top_role:
            raise PermissionsFailure(
                f"Your top role is higher than mine. I can't change your nickname :(")
        
        return True
    return commands.check(predicate)