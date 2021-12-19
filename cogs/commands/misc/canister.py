import json
import re
import traceback
import urllib

import aiohttp
import discord
from data.services.guild_service import guild_service
from discord.commands import Option, slash_command
from discord.ext import commands
from utils.autocompleters import fetch_repos, repo_autocomplete
from utils.config import cfg
from utils.context import BlooContext, BlooOldContext
from utils.logger import logger
from utils.menu import TweakMenu
from utils.views.canister import TweakDropdown, default_repos
from utils.permissions.checks import PermissionsFailure
from utils.permissions.permissions import permissions


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
        async with client.get(f'https://api.canister.me/v1/community/packages/search?query={urllib.parse.quote(query)}&searchFields=name,author,maintainer,description&responseFields=identifier,header,tintColor,name,price,description,packageIcon,repository.uri,repository.name,author,maintainer,latestVersion,nativeDepiction,depiction') as resp:
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


async def canister_repo(ctx: BlooContext, interaction: bool, whisper: bool, result):
    if not result:
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

        ctx = await self.bot.get_context(message, cls=BlooOldContext)

        async with ctx.typing():
            result = list(await search(search_term))

        if not result:
            raise commands.BadArgument("That package wasn't found in Canister's database.")
            return

        view = discord.ui.View(timeout=30)
        td = TweakDropdown(author, result, interaction=False, should_whisper=False)
        view.add_item(td)
        td.refresh_view(result[0])
        view.on_timeout = td.on_timeout
        message = await ctx.send(embed = await td.format_tweak_page(result[0]), view=view)
        new_ctx = await self.bot.get_context(message, cls=BlooOldContext)
        td.start(new_ctx)

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
        if len(query) < 2:
            raise commands.BadArgument("Please enter a longer query.")

        should_whisper = False
        if not permissions.has(ctx.guild, ctx.author, 5) and ctx.channel.id == guild_service.get_guild().channel_general:
            should_whisper = True

        await ctx.defer(ephemeral=should_whisper)
        result = list(await search(query))

        if not result:
            raise commands.BadArgument("That package wasn't found in Canister's database.")

        view = discord.ui.View(timeout=30)
        td = TweakDropdown(ctx.author, result, interaction=True, should_whisper=should_whisper)
        view.on_timeout = td.on_timeout
        view.add_item(td)
        td.refresh_view(result[0])
        await ctx.respond(embed = await td.format_tweak_page(result[0]), view=view)
        td.start(ctx)

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

        if result:
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
