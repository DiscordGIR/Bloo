import discord
import re
import aiohttp
from urllib.request import Request, urlopen
from discord.ext import commands
from yarl import URL
from data.services.guild_service import guild_service
from utils.permissions.permissions import permissions


class RepoWatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id == guild_service.get_guild().channel_general and not permissions.has(message.guild, message.author, 5):
            return
        
        url = re.search(r'(https?://\S+)', message.content)
        if url is None:
            return

        try:
            async with aiohttp.ClientSession() as client:
                async with client.get(URL(f'{url.group(0)}', encoded=True)) as resp:
                    req = Request(url.group(0)+'/Release')
                    # some repos need this, looking at you Chariz...
                    req.add_header('User-Agent', 'Sileo/2.5.6 CoreFoundation/1770.300 Darwin/20.2.0')
                    if urlopen(req).code == 200:
                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(label='Add Repo', url=f"https://sharerepo.stkc.win/?repo={url.group(0)}", emoji=":cydiasileosplit:932650041099825232", style=discord.ButtonStyle.url))
                        await message.reply(file=discord.File("data/images/transparent1x1.png") , view=view, mention_author=False)
        except: pass


def setup(bot):
    bot.add_cog(RepoWatcher(bot))
