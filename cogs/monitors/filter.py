
from datetime import timezone

import discord
from discord.errors import NotFound

from data.services.guild_service import guild_service
from discord.ext import commands
from utils.config import cfg
from utils.mod.filter import find_triggered_filters
from utils.mod.global_modactions import mute
from utils.mod.report import report

import re

from utils.permissions.permissions import permissions


class Xp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_filter = r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)\/{1,}[a-zA-Z0-9]+/?'
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(
            2, 10.0, commands.BucketType.member)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.guild.id != cfg.guild_id:
            return
        if message.author.bot:
            return
        if not message.content:
            return

        # run through filters
        db_guild = guild_service.get_guild()
        if await self.bad_word_filter(message, db_guild): return
        if await self.do_invite_filter(message, db_guild): return

    async def bad_word_filter(self, message, db_guild) -> bool:
        triggered_words = find_triggered_filters(
            message.content, message.author)
        if not triggered_words:
            return

        dev_role = message.guild.get_role(db_guild.role_dev)

        # TODO: test this thoroughly
        should_delete = False
        for word in triggered_words:
            if word.piracy:
                # ignore if it's a dev saying piracy in #development
                if message.channel.id == db_guild.channel_development and dev_role in message.author.roles:
                    continue

            if word.notify:
                await self.delete(message)
                await self.ratelimit(message)
                await report(self.bot, message, word.word)
                return

            should_delete = True

        if should_delete:
            await self.delete(message)
            await self.ratelimit(message)
        
        return should_delete
    
    async def do_invite_filter(self, message, db_guild):
        """
        INVITE FILTER
        """
        if permissions.has(message.guild, message.author, 5):
            return False
        
        invites = re.findall(self.invite_filter, message.content, flags=re.S)
        if not invites: return

        whitelist = db_guild.filter_excluded_guilds
        for invite in invites:
            try:
                invite = await self.bot.fetch_invite(invite)

                id = None
                if isinstance(invite, discord.Invite):
                    if invite.guild is not None:
                        id = invite.guild.id
                    else:
                        id = 123
                elif isinstance(invite, discord.PartialInviteGuild) or isinstance(invite, discord.PartialInviteChannel):
                    id = invite.id

                if id not in whitelist:
                    await self.delete(message)
                    await self.ratelimit(message)
                    await report(self.bot, message, invite, invite=invite)
                    return True

            except NotFound:
                await self.delete(message)
                await self.ratelimit(message)
                await self.report.report(message, message.author, invite, invite=invite)
                return True

        return False

    async def ratelimit(self, message):
        current = message.created_at.replace(tzinfo=timezone.utc).timestamp()
        bucket = self.spam_cooldown.get_bucket(message)
        if bucket.update_rate_limit(current):
            try:
                ctx = await self.bot.get_context(message)
                ctx.author = ctx.guild.me
                await mute(ctx, message.author, dur_seconds=15*60, reason="Filter spam")
            except Exception:
                return

    async def delete(self, message):
        try:
            await message.delete()
        except Exception:
            pass


def setup(bot):
    bot.add_cog(Xp(bot))
