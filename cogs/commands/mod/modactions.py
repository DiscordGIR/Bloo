from typing import Union
from discord.user import User
from discord.commands import Option, slash_command
from discord.ext import commands
from discord.member import Member
from discord.utils import escape_markdown
from data.model.case import Case
from data.model.guild import Guild
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from utils.checks import mod_and_up, whisper
from utils.config import cfg
from utils.context import BlooContext
from utils.converters import mods_and_above_external_resolver, user_resolver
from utils.slash_perms import slash_perms
from utils.mod_logs import prepare_warn_log


"""
Make sure to add the cog to the initial_extensions list
in main.py
"""

class ModActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @whisper()
    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Warn a user", permissions=slash_perms.mod_and_up())
    async def warn(self, ctx: BlooContext, user: Option(Member, description="User to warn"), points:Option(int, description="Amount of points to warn for"), reason: Option(str, description="Reason for warn", required=False) = "No reason."):
        """Warn a user (mod only)

        Example usage
        --------------
        !warn <@user/ID> <points> <reason (optional)>
        
        Parameters
        ----------
        user : discord.Member
            "The member to warn"
        points : int
            "Number of points to warn far"
        reason : str, optional
            "Reason for warning, by default 'No reason.'"

        """
        user = await mods_and_above_external_resolver(ctx, user)
        
        if points < 1:  # can't warn for negative/0 points
            raise commands.BadArgument(message="Points can't be lower than 1.")

        db_guild = guild_service.get_guild()

        reason = escape_markdown(reason)

        # prepare the case object for database
        case = Case(
            _id=db_guild.case_id,
            _type="WARN",
            mod_id=ctx.author.id,
            mod_tag=str(ctx.author),
            reason=reason,
            punishment=str(points)
        )

        # increment case ID in database for next available case ID
        guild_service.inc_caseid()
        # add new case to DB
        user_service.add_case(user.id, case)
        # add warnpoints to the user in DB
        user_service.inc_points(user.id, points)

        # fetch latest document about user from DB
        db_user = user_service.get_user(user.id)
        cur_points = db_user.warn_points

        # prepare log embed, send to #public-mod-logs, user, channel where invoked
        log = await prepare_warn_log(ctx.author, user, case)
        log.add_field(name="Current points", value=cur_points, inline=True)

        # also send response in channel where command was called
        dmed = await self.notify_user_warn(ctx, user, db_user, db_guild, cur_points, log)
        await ctx.respond(embed=log, delete_after=10)
        await self.submit_public_log(ctx, db_guild, user, log, dmed)

    async def notify_user_warn(self, ctx: BlooContext, user: User, db_user, db_guild, cur_points: int, log):
        log_kickban = None
        dmed = True
        
        if cur_points >= 600:
            # automatically ban user if more than 600 points
            try:
                await user.send(f"You were banned from {ctx.guild.name} for reaching 600 or more points.", embed=log)
            except Exception:
                dmed = False

            log_kickban = await self.add_ban_case(ctx, user, "600 or more warn points reached.")
            await user.ban(reason="600 or more warn points reached.")

        elif cur_points >= 400 and not db_user.was_warn_kicked and isinstance(user, Member):
            # kick user if >= 400 points and wasn't previously kicked
            user_service.set_warn_kicked(user.id)

            try:
                await user.send(f"You were kicked from {ctx.guild.name} for reaching 400 or more points. Please note that you will be banned at 600 points.", embed=log)
            except Exception:
                dmed = False

            log_kickban = await self.add_kick_case(ctx, user, "400 or more warn points reached.")
            await user.kick(reason="400 or more warn points reached.")

        else:
            if isinstance(user, Member):
                try:
                    await user.send(f"You were warned in {ctx.guild.name}. Please note that you will be kicked at 400 points and banned at 600 points.", embed=log)
                except Exception:
                    dmed = False
        
        if log_kickban:
            await self.submit_public_kickban_log(ctx, db_guild, user, log_kickban)

        return dmed

    async def submit_public_log(self, ctx: BlooContext, db_guild: Guild, user: Union[Member, User], log, dmed: bool):
        
        public_chan = ctx.guild.get_channel(
            db_guild.channel_public)
        if public_chan:
            log.remove_author()
            log.set_thumbnail(url=user.display_avatar)
            await public_chan.send(user.mention if not dmed else "", embed=log)

    async def submit_public_kickban_log(self, ctx: BlooContext, db_guild: Guild, user: Union[Member, User], log):
        public_chan = ctx.guild.get_channel(
            db_guild.channel_public)
        log.remove_author()
        log.set_thumbnail(url=user.display_avatar)
        await public_chan.send(embed=log)


def setup(bot):
    bot.add_cog(ModActions(bot))
