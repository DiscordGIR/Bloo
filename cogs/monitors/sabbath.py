from datetime import timezone
import traceback
import discord
from discord.commands.commands import Option, slash_command
from discord.ext import commands

from data.services.guild_service import guild_service
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.permissions import permissions
from utils.logger import logger
from utils.permissions.checks import PermissionsFailure, guild_owner_and_up
from utils.permissions.slash_perms import slash_perms

class Sabbath(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(
            1, 300.0, commands.BucketType.member)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.guild.id != cfg.guild_id:
            return
        if message.author.bot:
            return

        # check if message pings aaron or owner role:
        if not (cfg.aaron_id in message.raw_mentions or cfg.aaron_role in message.raw_role_mentions):
            return

        if not guild_service.get_guild().sabbath_mode:
            return

        if permissions.has(message.guild, message.author, 5):
            return

        current = message.created_at.replace(tzinfo=timezone.utc).timestamp()
        bucket = self.spam_cooldown.get_bucket(message)
        if bucket.update_rate_limit(current):
            return

        await message.channel.send(f"<@{cfg.aaron_id}> is away on Sabbath, he will get back to you as soon as possible!", allowed_mentions=discord.AllowedMentions(users=False))

    @guild_owner_and_up()
    @slash_command(description="Make bot say something", permissions=slash_perms.guild_owner_and_up())
    async def sabbath(self, ctx: BlooContext, mode: Option(bool, description="Set mode on or off", required=False) = None):
        g = guild_service.get_guild()
        g.sabbath_mode = mode if mode is not None else not g.sabbath_mode
        g.save()

        await ctx.send_success(f"Set sabbath mode to {'on' if g.sabbath_mode else 'off'}!")

    @sabbath.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, discord.ApplicationCommandInvokeError):
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
            logger.error(traceback.format_exc())


def setup(bot):
    if cfg.aaron_id is None or cfg.aaron_role is None:
        logger.warn(
            "Aaron's ID or role not set, disabling the Sabbath cog! If you want this, refer to README.md.")
        return

    bot.add_cog(Sabbath(bot))
