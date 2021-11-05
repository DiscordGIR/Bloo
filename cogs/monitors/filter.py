
import discord
from discord.ext import commands
from data.services.guild_service import guild_service
from utils.config import cfg
from utils.filter import find_triggered_filters
from utils.report import report

class Xp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
                await report(self.bot, message, word)
                return

            should_delete = True

        if should_delete:
            await message.delete()


def setup(bot):
    bot.add_cog(Xp(bot))
