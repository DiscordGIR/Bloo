
from datetime import timezone
import discord
from discord.ext import commands
from data.services.guild_service import guild_service
from utils.config import cfg
from utils.mod.filter import find_triggered_filters
from utils.mod.report import report

class Xp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(2, 10.0, commands.BucketType.user)
    

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.guild.id != cfg.guild_id:
            return
        if message.author.bot:
            return

        triggered_words = find_triggered_filters(message.content, message.author)
        if not triggered_words:
            return

        db_guild = guild_service.get_guild()
        dev_role = message.guild.get_role(db_guild.role_dev)

        # TODO: test this thoroughly
        should_delete = False
        for word in triggered_words:
            if word.piracy:
                # ignore if it's a dev saying piracy in #development
                if message.channel.id == db_guild.channel_development and dev_role in message.author.roles:
                    continue

            if word.notify:
                await message.delete()
                await self.ratelimit(message)
                await report(self.bot, message, word)
                return

            should_delete = True

        if should_delete:
            await message.delete()
            await self.ratelimit(message)

    async def ratelimit(self, message):
        current = message.created_at.replace(tzinfo=timezone.utc).timestamp()
        print("trigger")
        bucket = self.spam_cooldown.get_bucket(message)
        if bucket.update_rate_limit(current):
            ctx = await self.bot.get_context(message)
            # await self.mute(ctx, message.author)

def setup(bot):
    bot.add_cog(Xp(bot))
