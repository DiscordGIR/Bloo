import traceback
from datetime import datetime

import discord
from discord.commands import Option, slash_command
import pytz
from discord.ext import commands, tasks
from utils.autocompleters import date_autocompleter
from utils.context import BlooContext
from utils.config import cfg
from data.services.user_service import user_service
from data.services.guild_service import guild_service
from utils.logger import logger
from utils.mod.give_birthday_role import MONTH_MAPPING, give_user_birthday_role
from utils.permissions.checks import PermissionsFailure, whisper
from utils.permissions.permissions import permissions


class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.eastern_timezone = pytz.timezone('US/Eastern')
        self.birthday.start()

    def cog_unload(self):
        self.birthday.cancel()

    @tasks.loop(seconds=120)
    async def birthday(self):
        """Background task to scan database for users whose birthday it is today.
        If it's someone's birthday, the bot will assign them the birthday role for 24 hours."""

        # assign the role at 12am US Eastern time
        eastern = pytz.timezone('US/Eastern')
        today = datetime.today().astimezone(eastern)
        # the date we will check for in the database
        date = [today.month, today.day]
        # get list of users whose birthday it is today
        birthdays = user_service.retrieve_birthdays(date)

        guild = self.bot.get_guild(cfg.guild_id)
        if not guild:
            return

        db_guild = guild_service.get_guild()
        birthday_role = guild.get_role(db_guild.role_birthday)
        if not birthday_role:
            return

        # give each user whose birthday it is today the birthday role
        for person in birthdays:
            if person.birthday_excluded:
                continue

            user = guild.get_member(person._id)
            if user is None:
                return

            await give_user_birthday_role(self.bot, db_guild, user, guild)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Set your birthday. The birthday role will be given to you on that day.")
    async def mybirthday(self, ctx: BlooContext, month: Option(str, choices=list(MONTH_MAPPING.keys())), date: Option(int, autocomplete=date_autocompleter)) -> None:
        """Set your birthday. The birthday role will be given to you on that day. THIS COMMAND IS ONE TIME USE ONLY!

        Example usage
        --------------
        !mybirthday 7 18

        Parameters
        ----------
        month : int
            "Month of birthday"
        date : int
            "Date of birthday"
        """

        user = ctx.author

        if not (permissions.has(ctx.guild, ctx.author, 1) or user.premium_since is not None):
            raise commands.BadArgument(
                "You need to be at least Member+ or a Nitro booster to use that command.")

        month = MONTH_MAPPING.get(month)
        if month is None:
            raise commands.BadArgument("You gave an invalid date")

        month = month["value"]

        # ensure date is real (2020 is a leap year in case the birthday is leap day)
        try:
            datetime(year=2020, month=month, day=date, hour=12)
        except ValueError:
            raise commands.BadArgument("You gave an invalid date.")

        # fetch user profile from DB
        db_user = user_service.get_user(user.id)

        # mods are able to ban users from using birthdays, let's handle that
        if db_user.birthday_excluded:
            raise commands.BadArgument("You are banned from birthdays.")

        # if the user already has a birthday set in the database, refuse to change it (if not a mod)
        if db_user.birthday != [] and not permissions.has(ctx.guild, ctx.author, 5):
            raise commands.BadArgument(
                "You already have a birthday set! You need to ask a mod to change it.")

        # passed all the sanity checks, let's save the birthday
        db_user.birthday = [month, date]
        db_user.save()

        await ctx.send_success(f"Your birthday was set.")
        # if it's the user's birthday today let's assign the role right now!
        today = datetime.today().astimezone(self.eastern_timezone)
        if today.month == month and today.day == date:
            db_guild = guild_service.get_guild()
            await give_user_birthday_role(self.bot, db_guild, ctx.author, ctx.guild)

    @mybirthday.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, discord.ApplicationCommandInvokeError):
            error = error.original

        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MissingPermissions)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error(error)
            logger.error(traceback.format_exc())


def setup(bot):
    bot.add_cog(Birthday(bot))
