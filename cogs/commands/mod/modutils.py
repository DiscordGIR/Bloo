import datetime
import traceback

import discord
import pytz
from data.model.case import Case
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands.commands import Option, slash_command
from discord.commands.errors import ApplicationCommandInvokeError
from discord.ext import commands
from discord.utils import format_dt
from utils.autocompleters import date_autocompleter
from utils.config import cfg
from utils.context import BlooContext
from utils.mod.give_birthday_role import MONTH_MAPPING
from utils.permissions.checks import (PermissionsFailure, admin_and_up,
                                      guild_owner_and_up, mod_and_up, whisper)
from utils.permissions.slash_perms import slash_perms


class ModUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Get information about a user (join/creation date, xp, etc.)", permissions=slash_perms.mod_and_up())
    async def rundown(self, ctx: BlooContext, user: discord.Member):
        await ctx.respond(embed = await self.prepare_rundown_embed(ctx, user))

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Transfer all data in the database between users", permissions=slash_perms.admin_and_up())
    async def transferprofile(self, ctx: BlooContext, oldmember: discord.Member, newmember: discord.Member):
        if isinstance(oldmember, int):
            try:
                oldmember = await self.bot.fetch_user(oldmember)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {oldmember}")

        if isinstance(newmember, int):
            try:
                newmember = await self.bot.fetch_user(newmember)
            except discord.NotFound:
                raise commands.BadArgument(
                    f"Couldn't find user with ID {newmember}")

        u, case_count = user_service.transfer_profile(oldmember.id, newmember.id)

        embed = discord.Embed(title="Transferred profile")
        embed.description = f"We transferred {oldmember.mention}'s profile to {newmember.mention}"
        embed.color = discord.Color.blurple()
        embed.add_field(name="Level", value=u.level)
        embed.add_field(name="XP", value=u.xp)
        embed.add_field(name="Warnpoints", value=f"{u.warn_points} points")
        embed.add_field(name="Cases", value=f"We tranferred {case_count} cases")

        await ctx.respond(embed=embed)

        try:
            await newmember.send(f"{ctx.author} has transferred your profile from {oldmember}", embed=embed)
        except Exception:
            pass

    @guild_owner_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Sets user's XP and Level to 0, freezes XP, sets warn points to 599", permissions=slash_perms.guild_owner_and_up())
    async def clem(self, ctx: BlooContext, user: discord.Member):
        if user.id == ctx.author.id:
            await ctx.send_error("You can't call that on yourself.")
            raise commands.BadArgument("You can't call that on yourself.")
        if user.id == self.bot.user.id:
            await ctx.send_error("You can't call that on me :(")
            raise commands.BadArgument("You can't call that on me :(")

        results = user_service.get_user(user.id)
        results.is_clem = True
        results.is_xp_frozen = True
        results.warn_points = 599
        results.save()

        case = Case(
            _id=guild_service.get_guild().case_id,
            _type="CLEM",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            punishment=str(-1),
            reason="No reason."
        )

        # incrememnt DB's max case ID for next case
        guild_service.inc_caseid()
        # add case to db
        user_service.add_case(user.id, case)

        await ctx.send_success(f"{user.mention} was put on clem.")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Freeze a user's XP", permissions=slash_perms.admin_and_up())
    async def freezexp(self, ctx: BlooContext, user: discord.Member):
        results = user_service.get_user(user.id)
        results.is_xp_frozen = not results.is_xp_frozen
        results.save()

        await ctx.send_success(f"{user.mention}'s xp was {'frozen' if results.is_xp_frozen else 'unfrozen'}.")

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="", permissions=slash_perms.mod_and_up())
    async def musicban(self, ctx: BlooContext, user: discord.Member):
        if user.id == self.bot.user.id:
            await ctx.send_error("You can't call that on me :(")
            raise commands.BadArgument("You can't call that on me :(")

        results = user_service.get_user(user.id)
        results.is_music_banned = True
        results.save()

        await ctx.send_success(f"{user.mention} was banned from music.")


    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Ban a user from birthdays", permissions=slash_perms.mod_and_up())
    async def birthdayexclude(self, ctx: BlooContext, user: discord.Member):
        if user.id == self.bot.user.id:
            await ctx.send_error("You can't call that on me :(")
            raise commands.BadArgument("You can't call that on me :(")
        
        results = user_service.get_user(user.id)
        results.birthday_excluded = True
        results.birthday = None
        results.save()

        birthday_role = ctx.guild.get_role(guild_service.get_guild().role_birthday)
        if birthday_role is None:
            return
        
        if birthday_role in user.roles:
            await user.remove_roles(birthday_role)

        await ctx.send_success(f"{user.mention} was banned from birthdays.")

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Remove a user's birthday", permissions=slash_perms.mod_and_up())
    async def removebirthday(self, ctx: BlooContext, user: discord.Member):
        if user.id == self.bot.user.id:
            await ctx.send_error("You can't call that on me :(")
            raise commands.BadArgument("You can't call that on me :(")

        results = user_service.get_user(user.id)
        results.birthday = None
        results.save()

        try:
            ctx.tasks.cancel_unbirthday(user.id)
        except Exception:
            pass

        birthday_role = ctx.guild.get_role(guild_service.get_guild().role_birthday)
        if birthday_role is None:
            return

        if birthday_role in user.roles:
            await user.remove_roles(birthday_role)

        await ctx.send_success(f"{user.mention}'s birthday was removed.")

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Override a user's birthday", permissions=slash_perms.mod_and_up())
    async def setbirthday(self, ctx: BlooContext, user: discord.Member, month: Option(str, choices=list(MONTH_MAPPING.keys())), date: Option(int, autocomplete=date_autocompleter)):
        month = MONTH_MAPPING.get(month)
        if month is None:
            raise commands.BadArgument("You gave an invalid date")

        month = month["value"]
        
        if user.id == self.bot.user.id:
            await ctx.send_error("You can't call that on me :(")
            raise commands.BadArgument("You can't call that on me :(")
        
        try:
            datetime.datetime(year=2020, month=month, day=date, hour=12)
        except ValueError:
            raise commands.BadArgument("You gave an invalid date.")
        

        results = user_service.get_user(user.id)
        results.birthday = [month, date]
        results.save()

        await ctx.send_success(f"{user.mention}'s birthday was set.")

        if results.birthday_excluded:
            return
        
        eastern = pytz.timezone('US/Eastern')
        today = datetime.datetime.today().astimezone(eastern)
        if today.month == month and today.day == date:
            birthday_role = ctx.guild.get_role(guild_service.get_guild().role_birthday)
            if birthday_role is None:
                return
            if birthday_role in user.roles:
                return
            now = datetime.datetime.now(eastern)
            h = now.hour / 24
            m = now.minute / 60 / 24

            try:
                time = now + datetime.timedelta(days=1-h-m)
                ctx.tasks.schedule_remove_bday(user.id, time)
            except Exception:
                return

            await user.add_roles(birthday_role)
            await user.send(f"According to my calculations, today is your birthday! We've hiven you the {birthday_role} role for 24 hours.")

    async def prepare_rundown_embed(self, ctx: BlooContext, user):
        user_info = user_service.get_user(user.id)
        rd = user_service.rundown(user.id)
        rd_text = ""
        for r in rd:
            if r._type == "WARN":
                r.punishment += " points"
            rd_text += f"**{r._type}** - {r.punishment} - {r.reason} - {format_dt(r.date, style='R')}\n"

        reversed_roles = user.roles
        reversed_roles.reverse()

        roles = ""
        for role in reversed_roles[0:4]:
            if role != user.guild.default_role:
                roles += role.mention + " "
        roles = roles.strip() + "..."

        embed = discord.Embed(title="Rundown")
        embed.color = user.color
        embed.set_thumbnail(url=user.display_avatar)

        embed.add_field(name="Member", value=f"{user} ({user.mention}, {user.id})")
        embed.add_field(name="Join date", 
                        value=f"{format_dt(user.joined_at, style='F')} ({format_dt(user.joined_at, style='R')})")
        embed.add_field(name="Account creation date",
                        value=f"{format_dt(user.created_at, style='F')} ({format_dt(user.created_at, style='R')})")
        embed.add_field(name="Warn points",
                        value=user_info.warn_points, inline=True)

        if user_info.is_clem:
            embed.add_field(
                name="XP", value="*this user is clemmed*", inline=True)
        else:
            embed.add_field(
                name="XP", value=f"{user_info.xp} XP", inline=True)
            embed.add_field(
                name="Level", value=f"Level {user_info.level}", inline=True)

        embed.add_field(
            name="Roles", value=roles if roles else "None", inline=False)

        if len(rd) > 0:
            embed.add_field(name=f"{len(rd)} most recent cases",
                            value=rd_text, inline=False)
        else:
            embed.add_field(name=f"Recent cases",
                            value="This user has no cases.", inline=False)

        return embed

    @rundown.error
    @transferprofile.error
    @clem.error
    @freezexp.error
    @musicban.error
    @birthdayexclude.error
    @removebirthday.error
    @setbirthday.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, ApplicationCommandInvokeError):
            error = error.original
        
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error("A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()


def setup(bot):
    bot.add_cog(ModUtils(bot))
