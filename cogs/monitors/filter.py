
import discord
from discord.ext import commands
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
        # guild_service.get_guild().channel_botspam:
        triggered_words = find_triggered_filters(message.content, message.author)
        if not triggered_words:
            return

        await message.delete()
        for word in triggered_words:
            if word.notify:
                await report(self.bot, message, word)
                return


def setup(bot):
    bot.add_cog(Xp(bot))
