import discord
from discord.commands import Option, slash_command
from discord.ext import commands

import io
import json
import re
import traceback
import urllib
import aiohttp
from datetime import datetime
from colorthief import ColorThief
from data.services.guild_service import guild_service
from utils.config import cfg
from utils.context import BlooContext
from utils.logger import logger
from utils.database import Guild
from utils.menu import TweakMenu
from utils.permissions.checks import PermissionsFailure
from utils.permissions.permissions import permissions

default_repos = [
    "apt.bingner.com",
    "apt.procurs.us",
    "apt.saurik.com",
    "apt.oldcurs.us",
    "repo.chimera.sh",
    "diatr.us/apt",
    "repo.theodyssey.dev",
]

async def format_page(entries, all_pages, current_page, ctx):
    """Formats the page for the tweak embed.
    
    Parameters
    ----------
    entries : List[dict]
        "The list of dictionaries for each tweak"
    all_pages : list
        "All entries that we will eventually iterate through"
    current_page : number
        "The number of the page that we are currently on"
        
    Returns
    -------
    discord.Embed
        "The embed that we will send"
    
    """
    entry = entries[0]
    ctx.repo = entry.get('repository').get('uri')
    for repo in default_repos:
        if repo in entry.get('repository').get('uri'):
            ctx.repo = None
            break
    titleKey = entry.get('name')
    if entry.get('name') is None:
        titleKey = entry.get('identifier')
    embed = discord.Embed(title=titleKey, color=discord.Color.blue())
    embed.description = discord.utils.escape_markdown(entry.get('description')) or "No description"
    if entry.get('author') is not None:
        embed.add_field(name="Author", value=discord.utils.escape_markdown(entry.get('author').split("<")[0]), inline=True)
    else:
        embed.add_field(name="Author", value=discord.utils.escape_markdown(entry.get('maintainer').split("<")[0]), inline=True)
    embed.add_field(name="Version", value=discord.utils.escape_markdown(entry.get('latestVersion') or "No Version"), inline=True)
    embed.add_field(name="Price", value=entry.get("price") or "Free", inline=True)
    embed.add_field(name="Repo", value=f"[{entry.get('repository').get('name')}]({entry.get('repository').get('uri')})" or "No Repo", inline=True)
    embed.add_field(name="Add Repo", value=f"[Click Here](https://sharerepo.stkc.win/?repo={entry.get('repository').get('uri')})" or "No Repo", inline=True)
    pattern = re.compile(r"((http|https)\:\/\/)[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*")
    if entry.get('tintColor') is None and entry.get('packageIcon') is not None and pattern.match(entry.get('packageIcon')):
        async with aiohttp.ClientSession() as session:
            async with session.get(entry.get('packageIcon')) as icon:
                color = ColorThief(io.BytesIO(await icon.read())).get_color(quality=1)
                embed.color = discord.Color.from_rgb(
                    color[0], color[1], color[2])
    elif entry.get('tintColor') is not None:
        embed.color = int(entry.get('tintColor').replace('#', '0x'), 0)
    if entry.get('packageIcon') is not None and pattern.match(entry.get('packageIcon')):
        embed.set_thumbnail(url=entry.get('packageIcon'))
    embed.set_footer(icon_url=f"{entry.get('repository').get('uri')}/CydiaIcon.png", text=discord.utils.escape_markdown(
        f"{entry.get('repository').get('name')} • Page {current_page}/{len(all_pages)}" or "No Package"))
    embed.timestamp = datetime.now()
    return embed

async def search(query):
    """Search for a tweak in Canister's catalogue

    Parameters
    ----------
    query : str
        "Query to search for"

    Returns
    -------
    list
        "List of packages that Canister found matching the query"
    
    """
    async with aiohttp.ClientSession() as client:
        async with client.get(f'https://api.canister.me/v1/community/packages/search?query={urllib.parse.quote(query)}&searchFields=identifier,name&responseFields=identifier,header,tintColor,name,price,description,packageIcon,repository.uri,repository.name,author,maintainer,latestVersion,nativeDepiction,depiction') as resp:
            if resp.status == 200:
                response = json.loads(await resp.text())
                if response.get('status') == "Successful":
                    return response.get('data')
                else:
                    return None
            else:
                return None

async def canister(bot, ctx: BlooContext, interaction: bool, whisper: bool, query: str):
    async with ctx.typing():
        result = list(await search(query))
    if len(result) == 0:
        if interaction is True:
            await ctx.send_error("That package isn't registered with Canister's database.")
        return
    await TweakMenu(result, ctx.channel, format_page, interaction, ctx, whisper, no_skip=True).start()

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

        pattern = re.compile(
            r".*?(?<!\[)+\[\[((?!\s+)([\w+\ \&\+\-]){2,})\]\](?!\])+.*")
        if not pattern.match(message.content):
            return

        matches = pattern.findall(message.content)
        if not matches:
            return

        search_term = matches[0][0].replace('[[', '').replace(']]', '')
        if not search_term:
            return

        ctx = await self.bot.get_context(message)
        await canister(self.bot, ctx, False, False, search_term)

    @slash_command(guild_ids=[cfg.guild_id], description="Search for a package")
    async def package(self, ctx: BlooContext, query: Option(str, description="Name of the package to search for.")) -> None:
        """Search for a package.
        
        Example usage
        -------------
        /package query:<query>
        
        Parameters
        ----------
        query : str
            "Name of the package to search for"
        
        """
        should_whisper = False
        if not permissions.has(ctx.guild, ctx.author, 5) and ctx.channel.id == guild_service.get_guild().channel_general:
            should_whisper = True
            
        await canister(self.bot, ctx, True, should_whisper, query)

    @package.error
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
            await ctx.send_error("A fatal error occured. Tell <@848159481255034891> about this.")
            logger.error(traceback.format_exc())

def setup(bot):
    bot.add_cog(Canister(bot))
