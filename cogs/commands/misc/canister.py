import io
import json
import re
import traceback
import urllib
from datetime import datetime

import aiohttp
import discord
from aiocache import cached
from colorthief import ColorThief
from data.services.guild_service import guild_service
from discord.commands import Option, slash_command
from discord.commands.context import AutocompleteContext
from discord.ext import commands
from utils.autocompleters import fetch_repos, repo_autocomplete
from utils.config import cfg
from utils.context import BlooContext
from utils.logger import logger
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


pattern = re.compile(
    r"((http|https)\:\/\/)[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*")


async def format_tweak_page(entries, all_pages, current_page, ctx):
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
    ctx.depiction = entry.get('depiction')

    for repo in default_repos:
        if repo in entry.get('repository').get('uri'):
            ctx.repo = None
            break

    titleKey = entry.get('name')

    if entry.get('name') is None:
        titleKey = entry.get('identifier')
    embed = discord.Embed(title=titleKey, color=discord.Color.blue())
    embed.description = discord.utils.escape_markdown(
        entry.get('description')) or "No description"

    if entry.get('author') is not None:
        embed.add_field(name="Author", value=discord.utils.escape_markdown(
            entry.get('author').split("<")[0]), inline=True)
    else:
        embed.add_field(name="Author", value=discord.utils.escape_markdown(
            entry.get('maintainer').split("<")[0]), inline=True)

    embed.add_field(name="Version", value=discord.utils.escape_markdown(
        entry.get('latestVersion') or "No Version"), inline=True)
    embed.add_field(name="Price", value=entry.get(
        "price") or "Free", inline=True)
    embed.add_field(
        name="Repo", value=f"[{entry.get('repository').get('name')}]({entry.get('repository').get('uri')})" or "No Repo", inline=True)
    embed.add_field(name="Bundle ID", value=entry.get("identifier") or "Not found", inline=True)
    if entry.get('tintColor') is None and entry.get('packageIcon') is not None and pattern.match(entry.get('packageIcon')):
        async with aiohttp.ClientSession() as session:
            async with session.get(entry.get('packageIcon')) as icon:
                color = ColorThief(io.BytesIO(await icon.read())).get_color(quality=1000)
                embed.color = discord.Color.from_rgb(
                    color[0], color[1], color[2])
    elif entry.get('tintColor') is not None:
        embed.color = int(entry.get('tintColor').replace('#', '0x'), 0)

    if entry.get('packageIcon') is not None and pattern.match(entry.get('packageIcon')):
        embed.set_thumbnail(url=entry.get('packageIcon'))
    embed.set_footer(icon_url=f"{entry.get('repository').get('uri')}/CydiaIcon.png", text=f"Powered by Canister • Page {current_page}/{len(all_pages)}" or "No Package")
    embed.timestamp = datetime.now()
    return embed


async def format_repo_page(entries, all_pages, current_page, ctx):
    repo_data = entries[0]

    ctx.repo = repo_data.get('uri')
    for repo in default_repos:
        if repo in repo_data.get('uri'):
            ctx.repo = None
            break

    ctx.depiction = None

    embed = discord.Embed(title=repo_data.get(
        'name'), color=discord.Color.blue())
    embed.add_field(name="URL", value=repo_data.get('uri'), inline=True)
    embed.add_field(name="Version", value=repo_data.get(
        'version'), inline=True)

    embed.set_thumbnail(url=f'{repo_data.get("uri")}/CydiaIcon.png')
    embed.set_footer(text="Powered by Canister")

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


async def search_repo(query):
    """Search for a repo in Canister's catalogue

    Parameters
    ----------
    query : str
        "Query to search for"

    Returns
    -------
    list
        "List of repos that Canister found matching the query"

    """
    async with aiohttp.ClientSession() as client:
        async with client.get(f'https://api.canister.me/v1/community/repositories/search?query={urllib.parse.quote(query)}') as resp:
            if resp.status == 200:
                response = json.loads(await resp.text())
                if response.get('status') == "Successful":
                    return response.get('data')
                else:
                    return None
            else:
                return None


async def canister(ctx: BlooContext, interaction: bool, whisper: bool, result):
    if len(result) == 0:
        if interaction is True:
            await ctx.send_error("That package isn't registered with Canister's database.")
        return
    await TweakMenu(result, ctx.channel, format_tweak_page, interaction, ctx, whisper, no_skip=True).start()


async def canister_repo(ctx: BlooContext, interaction: bool, whisper: bool, result):
    if len(result) == 0:
        await ctx.send_error("That repository isn't registered with Canister's database.")
        return
    ctx.repo = result[0].get('uri')
    await TweakMenu(result, ctx.channel, format_repo_page, interaction, ctx, whisper, no_skip=True).start()


class Canister(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return

        author = message.guild.get_member(message.author.id)
        if author is None:
            return

        if not permissions.has(message.guild, author, 5) and message.channel.id == guild_service.get_guild().channel_general:
            return

        pattern = re.compile(
            r".*?(?<!\[)+\[\[((?!\s+)([\w+\ \&\+\-\<\>\#\:\;\%]){2,})\]\](?!\])+.*")
        if not pattern.match(message.content):
            return

        matches = pattern.findall(message.content)
        if not matches:
            return

        search_term = matches[0][0].replace('[[', '').replace(']]', '')
        if not search_term:
            return

        ctx = await self.bot.get_context(message)
        
        async with ctx.typing():
            result = list(await search(search_term))
        
        await canister(ctx, False, False, result)

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

        await ctx.defer(ephemeral=should_whisper)
        result = list(await search(query))
        await canister(ctx, True, should_whisper, result)

    @slash_command(guild_ids=[cfg.guild_id], description="Search for a repository")
    async def repo(self, ctx: BlooContext, query: Option(str, description="Name of the repository to search for.", autocomplete=repo_autocomplete)) -> None:
        """Search for a repo.

        Parameters
        ----------
            query : str
                "Name of the repository to search for"
        """
        repos = await fetch_repos()
        if query not in [repo['slug'] for repo in repos if repo.get("slug") and repo.get("slug") is not None]:
            await ctx.send_error("That repository isn't registered with Canister's database.")
            return
        should_whisper = False
        if not permissions.has(ctx.guild, ctx.author, 5) and ctx.channel.id == guild_service.get_guild().channel_general:
            should_whisper = True

        await ctx.defer(ephemeral=should_whisper)
        result = list(await search_repo(query))
        await canister_repo(ctx, True, should_whisper, result)

    @package.error
    @repo.error
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
    bot.add_cog(Canister(bot))
