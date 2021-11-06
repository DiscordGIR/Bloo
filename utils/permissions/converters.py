from discord.errors import NotFound
from discord.ext import commands
from discord.ext.commands.errors import BadArgument
from discord.member import Member
from utils.permissions import PermissionsFailure
from utils import BlooContext


async def mods_and_above_member_resolver(ctx: BlooContext, argument):
    if not isinstance(argument, Member):
        raise BadArgument("User must be in the guild.")
    await check_invokee(ctx, argument)
    return argument


async def mods_and_above_external_resolver(ctx: BlooContext, argument):
    if isinstance(argument, Member):
        user = argument
    else:
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


async def user_resolver(ctx: BlooContext, argument):
    try:
        argument = int(argument)
        user = await ctx.bot.fetch_user(argument)
    except Exception:
        raise PermissionsFailure("Could not parse argument \"user\".")
    except NotFound:
        raise PermissionsFailure(
            f"Couldn't find user with ID {argument}")
        
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

