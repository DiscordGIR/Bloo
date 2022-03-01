import asyncio
import re

import discord
from discord.ext import commands
from utils.config import cfg
from utils.mod.filter import find_triggered_filters

from utils.config import cfg

class TwitterFix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
      if not message.guild:
        return
      if message.guild.id != cfg.guild_id:
        return
      if message.content is None:
        return

      tweet_link = re.search(r"https://twitter\.com/[a-z0-9_]{1,15}/status/[\d+]{15,}", message.content)
      if tweet_link is None: 
        return

      triggered_words = find_triggered_filters(
            message.content, message.author)
      if triggered_words:
        return

      await asyncio.sleep(1)

      new_msg = await message.channel.fetch_message(message.id)
      if new_msg.embeds:
        return

      link = tweet_link.group(0)
      link = link.replace("twitter.com", "fxtwitter.com")
      await message.reply(link, allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False), mention_author=False)


def setup(bot):
    bot.add_cog(TwitterFix(bot))