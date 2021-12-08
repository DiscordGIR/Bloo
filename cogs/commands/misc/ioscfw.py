import traceback

import aiohttp
import discord
from aiocache.decorators import cached
from discord.commands import slash_command
from discord.commands.commands import Option
from discord.ext import commands
from utils.autocompleters import jb_autocomplete
from utils.config import cfg
from utils.context import BlooContext
from utils.logger import logger
from utils.permissions.checks import (PermissionsFailure,
                                      whisper_in_general)


@cached(ttl=3600)
async def get_jailbreaks_jba():
    """Gets all apps on Jailbreaks.app

    Returns
    -------
    dict
        "Apps"
    """
    res_apps = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://jailbreaks.app/json/apps.json") as resp:
            if resp.status == 200:
                res_apps = await resp.json()
    return res_apps


@cached(ttl=3600)
async def get_ios_cfw():
    """Gets all apps on ios.cfw.guide

    Returns
    -------
    dict
        "ios, jailbreaks, devices"
    """

    async with aiohttp.ClientSession() as session:
        async with session.get("https://ios.cfw.guide/main.json") as resp:
            if resp.status == 200:
                data = await resp.json()

    return data


@cached(ttl=1800)
async def get_signed_status():
    """Gets Jailbreaks.app's signed status"""
    signed = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://jailbreaks.app/status.php") as resp:
            if resp.status == 200:
                signed = await resp.json()
    return signed


async def iterate_apps(query) -> dict:
    """Iterates through Jailbreaks.app apps, looking for a matching query

    Parameters
    ----------
    query : str
        "App to look for"

    Returns
    -------
    dict
        "List of apps that match the query"

    """
    apps = await get_jailbreaks_jba()
    for possibleApp in apps:
        if possibleApp.get('name').lower() == query.lower().replace("œ", "oe"):
            return possibleApp


class iOSCFW(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @whisper_in_general()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info about a jailbreak.")
    async def jailbreak(self, ctx: BlooContext, name: Option(str, description="Name of the jailbreak", autocomplete=jb_autocomplete, required=True)) -> None:
        """Fetches info of jailbreak

        Example usage
        -------------
        /jailbreak name:<name>

        Parameters
        ----------
        name : str
            "Name of jailbreak"
        """
        response = await get_ios_cfw()

        matching_jbs = [jb for jb in response.get(
            "jailbreak") if jb.get("name").lower() == name.lower()]
        if not matching_jbs:
            raise commands.BadArgument("No jailbreak found with that name.")

        jb = matching_jbs[0]
        info = jb.get('info')

        color = info.get("color")
        if color is not None:
            color = int(color.replace("#", ""), 16)

        embed = discord.Embed(title=jb.get(
            'name'), color=color or discord.Color.random())
        view = discord.ui.View()

        if info is not None:
            embed.set_thumbnail(url=f"https://ios.cfw.guide{info.get('icon')}")

            embed.add_field(
                name="Version", value=info.get("latestVer"), inline=True)

            if info.get("firmwares"):
                soc = f"Works with {info.get('soc')}" if info.get(
                    'soc') else ""
                embed.add_field(name="Compatible with",
                                value=f'iOS {"-".join(info.get("firmwares"))}\n{f"**{soc}**" if soc else ""}', inline=True)
            else:
                embed.add_field(name="Compatible with",
                                value="Unavailable", inline=True)

            embed.add_field(
                name="Type", value=info.get("type"), inline=False)

            if info.get("website") is not None:
                view.add_item(discord.ui.Button(label='Website', url=info.get(
                    "website").get("url"), style=discord.ButtonStyle.url))

            if info.get('guide'):
                for guide in info.get('guide'):
                    view.add_item(discord.ui.Button(
                        label=f'{guide.get("name")} Guide', url=f"https://ios.cfw.guide{guide.get('url')}", style=discord.ButtonStyle.url))
            if info.get('notes') is not None:
                embed.add_field(
                    name="Notes", value=info.get('notes'), inline=False)

            embed.set_footer(text="Powered by https://ios.cfw.guide")
        else:
            embed.description = "No info available."

        jba = await iterate_apps(jb.get("name"))
        signed = await get_signed_status()
        if jba is not None and signed.get('status') == 'Signed':
            view.add_item(discord.ui.Button(label='Install with Jailbreaks.app',
                          url=f"https://api.jailbreaks.app/install/{jba.get('name').replace(' ', '')}", style=discord.ButtonStyle.url))
        else:
            view.add_item(discord.ui.Button(label='Install with Jailbreaks.app',
                          url=f"https://api.jailbreaks.app/install/{jba.get('name').replace(' ', '')}", style=discord.ButtonStyle.url, disabled=True))

        await ctx.respond_or_edit(embed=embed, ephemeral=ctx.whisper, view=view)

    @jailbreak.error
    async def info_error(self, ctx: BlooContext, error):
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
    bot.add_cog(iOSCFW(bot))
