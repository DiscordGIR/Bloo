import json
import aiohttp
import discord
from discord.ext import commands
import re
import pprint

from utils.config import cfg

platforms = {
    "spotify": {
        "name": "Spotify",
        "emote": "<:spotify:911031828444491806>"
    },
    "appleMusic": {
        "name": "Apple Music",
        "emote": "<:appleMusic:911031685511004160>"
    },
    "youtube": {
        "name": "YouTube",
        "emote": "<:youtube:911032125199908934>"
    },
    "tidal": {
        "name": "Tidal",
        "emote": "<:tidal:911047304868417586>"
    },
    "amazonMusic": {
        "name": "Amazon Music",
        "emote": "<:amazonMusic:911047410409689088>"
    },
}

class Songs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spotify_pattern = re.compile(r"[\bhttps://open.\b]*spotify[\b.com\b]*[/:]*track[/:]*[A-Za-z0-9?=]+")
        self.am_pattern = re.compile(r"[\bhttps://music.\b]*apple[\b.com\b]*[/:][[a-zA-Z][a-zA-Z]]?[:/][a-zA-Z]+[/:][a-zA-Z\d-]+[[/:][\d]*]*")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if cfg.aaron_id is None or cfg.aaron_role is None:
            return
        if not message.guild:
            return
        if message.guild.id != cfg.guild_id:
            return
        if message.author.bot:
            return

        spotify_match = self.spotify_pattern.match(message.content)
        if spotify_match:
            link = spotify_match.group(0)
            await self.generate_view(message, link)
            return
        
        am_match = self.am_pattern.match(message.content)
        if am_match:
            link = am_match.group(0)
            await self.generate_view(message, link)
            return
        
    async def generate_view(self, message: discord.Message, link: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.song.link/v1-alpha.1/links?url={link}') as resp:
                if resp.status != 200:
                    return None
                
                res = await resp.text()
                res = json.loads(res)

        view = discord.ui.View()
        for platform, body in platforms.items():
            platform_links = res.get('linksByPlatform').get(platform)
            if platform_links is not None:
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label=body["name"], emoji=body["emote"], url=platform_links.get('url')))

        await message.reply("Sick tunes bro!", view=view, mention_author=False)

def setup(bot):
    bot.add_cog(Songs(bot))
