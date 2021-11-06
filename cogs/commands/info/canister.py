import io
import json
import re
import urllib
from datetime import datetime

import aiohttp
import discord
from colorthief import ColorThief
from data.model import Guild
from discord.commands.commands import Option, slash_command
from discord.ext import commands
from utils import BlooContext, cfg
from utils.permissions import permissions


async def aiter(packages):
    for package in packages:
        yield package

class TweakMenu():
    def __init__(self, response, length):
        #super().__init__(response, per_page=1)
        self.page_length = length
        
    async def format_page(self, entry):
        embed = discord.Embed(title=entry.get('name'), color=discord.Color.blue())
        embed.description = discord.utils.escape_markdown(entry.get('description')) or "No description"
        embed.add_field(name="Author", value= discord.utils.escape_markdown(entry.get('author').split("<")[0] or "No Author"), inline=True)
        embed.add_field(name="Version", value= discord.utils.escape_markdown(entry.get('latestVersion') or "No Version"), inline=True)
        embed.add_field(name="Price", value=entry.get("price") or "Free")
        embed.add_field(name="Repo", value=f"[{entry.get('repository').get('name')}]({entry.get('repository').get('uri')})" or "No Repo", inline=True)
        embed.add_field(name="Add Repo", value=f"[Click Here](https://sharerepo.stkc.win/?repo={entry.get('repository').get('uri')})" or "No Repo", inline=True)
        pattern = re.compile(r"((http|https)\:\/\/)[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*")
        if entry.get('tintColor') is None:
            if (pattern.match(entry.get('packageIcon'))):
                async with aiohttp.ClientSession() as session:
                    async with session.get(entry.get('packageIcon')) as icon:
                        color = ColorThief(io.BytesIO(await icon.read())).get_color(quality=1)
                        embed.color = discord.Color.from_rgb(color[0], color[1], color[2])
        else:
            embed.color = int(entry.get('tintColor').replace('#', '0x'), 0)
        if (pattern.match(entry.get('packageIcon'))):
            embed.set_thumbnail(url=entry.get('packageIcon'))
        embed.set_footer(icon_url=f"{entry.get('repository').get('uri')}CydiaIcon.png", text=discord.utils.escape_markdown(entry.get('name'))+f" • Page 1/{self.page_length}" or "No Package")
        embed.timestamp = datetime.now()
        return embed

async def search(query):
    async with aiohttp.ClientSession() as client:
        async with client.get(f'https://api.canister.me/v1/community/packages/search?query={urllib.parse.quote(query)}&searchFields=identifier,name&responseFields=identifier,header,tintColor,name,price,description,packageIcon,repository.uri,repository.name,author,latestVersion,nativeDepiction,depiction') as resp:
            if resp.status == 200:
                response = json.loads(await resp.text())
                if response.get('status') == "Successful":
                    return response.get('data')
                else:
                    return None
            else:
                return None

async def canister(bot, ctx: BlooContext, interaction: bool, whisper: bool, query: str):
    result = await search(query)
    if not interaction:
        await bot.get_channel(ctx.channel.id).send(embed=(await TweakMenu(aiter(result), len(result)).format_page(result[0])))
    else:
        await ctx.respond(embed=(await TweakMenu(aiter(result), len(result)).format_page(result[0])), ephemeral=whisper)

class Canister(commands.Cog):
    def __init__(self, bot):
        self.regex = re.compile(r'/\[\[.*\]\]/g')
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return
        
        author = message.guild.get_member(message.author.id)
        if author is None:
            return
        
        if not permissions.has(message.guild, author, 5) and message.channel.id == Guild.channel_general:
            return
        
        pattern = re.compile(r".*?(?<!\[)+\[\[((?!\s+)([\w+\ \&\+\-]){2,})\]\](?!\])+.*")
        if not pattern.match(message.content):
            return
        
        matches = pattern.findall(message.content)
        if not matches:
            return

        search_term = matches[0][0].replace('[[', '').replace(']]','')
        if not search_term:
            return

        ctx = await self.bot.get_context(message)
        async with ctx.typing():
            await canister(self.bot, ctx, False, False, search_term)
            
    @slash_command(guild_ids=[cfg.guild_id], description="Add device to nickname")
    async def tweak(self, ctx: BlooContext, query: Option(str, description="Tweak to search for."), whisper: Option(bool, description="Whisper? (No by default)", required=False)) -> None:
        should_whisper = False
        if not permissions.has(ctx.guild, ctx.author, 5) and ctx.channel.id == Guild.channel_general:
            should_whisper = True
        else:
            should_whisper = whisper
        await canister(self.bot, ctx, True, should_whisper, query)
        
def setup(bot):
    bot.add_cog(Canister(bot))
