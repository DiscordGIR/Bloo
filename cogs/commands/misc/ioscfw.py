import datetime
import json
import traceback

import aiohttp
import discord
from aiocache.decorators import cached
from discord.commands import slash_command
from discord.commands.commands import Option
from discord.ext import commands
from utils.autocompleters import (device_autocomplete, device_autocomplete_jb,
                                  get_ios_cfw, ios_beta_version_autocomplete,
                                  ios_on_device_autocomplete,
                                  ios_version_autocomplete, jb_autocomplete, transform_groups)
from utils.config import cfg
from utils.context import BlooContext
from utils.logger import logger
from utils.menu import CIJMenu
from utils.permissions.checks import PermissionsFailure, whisper_in_general


async def format_jailbreak_page(entries, all_pages, current_page, ctx):
    jb = entries[0]
    info = jb.get('info')
    info['name'] = jb.get('name')
    ctx.jb_info = info

    color = info.get("color")
    if color is not None:
        color = int(color.replace("#", ""), 16)

    embed = discord.Embed(title="Good news, your device is jailbreakable!",
                          color=color or discord.Color.random())
    embed.description = f"{jb.get('name')} works on {ctx.device} on {ctx.version}!"

    if info is not None:
        embed.set_thumbnail(url=f"https://ios.cfw.guide{info.get('icon')}")

        embed.add_field(
            name="Version", value=info.get("latestVer"), inline=True)

        if info.get("firmwares"):
            soc = f"Works with {info.get('soc')}" if info.get(
                'soc') else ""

            firmwares = info.get("firmwares")
            if len(firmwares) > 2:
                firmwares = ", ".join(firmwares)
            else:
                firmwares = " - ".join(info.get("firmwares"))

            embed.add_field(name="Compatible with",
                            value=f'iOS {firmwares}\n{f"**{soc}**" if soc else ""}', inline=True)
        else:
            embed.add_field(name="Compatible with",
                            value="Unavailable", inline=True)

        embed.add_field(
            name="Type", value=info.get("type"), inline=False)

        if info.get('notes') is not None:
            embed.add_field(
                name="Notes", value=info.get('notes'), inline=False)

        embed.set_footer(
            text=f"Powered by https://ios.cfw.guide • Page {current_page} of {len(all_pages)}")
    else:
        embed.description = "No info available."

    return embed


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


@cached(ttl=1800)
async def get_signed_status():
    """Gets Jailbreaks.app's signed status"""
    signed = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://jailbreaks.app/status.php") as resp:
            if resp.status == 200:
                res = await resp.text()
                signed = json.loads(res)
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
    async def jailbreak(self, ctx: BlooContext, name: Option(str, description="Name of the jailbreak", autocomplete=jb_autocomplete, required=True), user_to_mention: Option(discord.Member, description="User to mention in the response", required=False)) -> None:
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

                firmwares = info.get("firmwares")
                if len(firmwares) > 2:
                    firmwares = ", ".join(firmwares)
                else:
                    firmwares = " - ".join(info.get("firmwares"))

                embed.add_field(name="Compatible with",
                                value=f'iOS {firmwares}\n{f"**{soc}**" if soc else ""}', inline=True)
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

            if info.get("jailbreaksmeapp") is not None:
                jba = await iterate_apps(jb.get("name"))
                signed = await get_signed_status()
                if jba is None or signed.get('status') != 'Signed':
                    view.add_item(discord.ui.Button(label='Install with Jailbreaks.app',
                                                    url=f"https://api.jailbreaks.app/", style=discord.ButtonStyle.url, disabled=True))
                else:
                    view.add_item(discord.ui.Button(label='Install with Jailbreaks.app',
                                                    url=f"https://api.jailbreaks.app/install/{jba.get('name').replace(' ', '')}", style=discord.ButtonStyle.url))

            embed.set_footer(text="Powered by https://ios.cfw.guide")
        else:
            embed.description = "No info available."

        if user_to_mention is not None:
            title = f"Hey {user_to_mention.mention}, have a look at this!"
        else:
            title = None

        await ctx.respond_or_edit(content=title, embed=embed, ephemeral=ctx.whisper, view=view)

    @whisper_in_general()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info about an iOS version.")
    async def firmware(self, ctx: BlooContext, version: Option(str, description="Version of the firmware", autocomplete=ios_version_autocomplete, required=True)) -> None:
        """Fetches info of an iOS version

        Example usage
        -------------
        /firmware version:<version>

        Parameters
        ----------
        version : str
            "Version of iOS"
        """

        response = await get_ios_cfw()
        ios = response.get("ios")
        ios = [ios for ios in ios if f"{ios.get('version')} ({ios.get('build')})" == version or ios.get(
            'build').lower() == version.lower() or ios.get('version').lower() == version.lower()]

        if not ios:
            raise commands.BadArgument("No firmware found with that version.")

        matching_ios = ios[0]
        await self.do_firmware_response(ctx, matching_ios)

    @whisper_in_general()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info about a beta iOS version.")
    async def betafirmware(self, ctx: BlooContext, version: Option(str, description="Version of the beta firmware", autocomplete=ios_beta_version_autocomplete, required=True)) -> None:
        """Fetches info of a beta iOS version

        Example usage
        -------------
        /betafirmware version:<version>

        Parameters
        ----------
        version : str
            "Version of beta iOS"
        """

        response = await get_ios_cfw()
        ios = response.get("ios")
        ios = [ios for ios in ios if (f"{ios.get('version')} ({ios.get('build')})" == version or ios.get(
            'build').lower() == version.lower() or ios.get('version').lower() == version.lower()) and ios.get('beta')]

        if not ios:
            raise commands.BadArgument("No firmware found with that version.")

        matching_ios = ios[0]
        await self.do_firmware_response(ctx, matching_ios)

    async def do_firmware_response(self, ctx, matching_ios):

        embed = discord.Embed(
            title=f"iOS {matching_ios.get('version')}", color=discord.Color.random())
        embed.add_field(name="Build number",
                        value=matching_ios.get("build"), inline=True)

        embed.add_field(name="Supported devices", value=len(
            matching_ios.get("devices")) or "None found", inline=True)

        release = matching_ios.get("released")
        if release is not None:
            try:
                release_date = datetime.datetime.strptime(release, "%Y-%m-%d")
                embed.add_field(
                    name="Release date", value=f"{discord.utils.format_dt(release_date, 'D')} ({discord.utils.format_dt(release_date, 'R')})", inline=False)
            except ValueError:
                embed.add_field(name="Release date",
                                value=release, inline=False)

        embed.set_footer(text="Powered by https://ios.cfw.guide")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="View more on ios.cfw.guide",
                      url=f"https://ios.cfw.guide/chart/firmware/{matching_ios.get('build')}"))

        await ctx.respond(embed=embed, view=view, ephemeral=ctx.whisper)

    @whisper_in_general()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info about an Apple device.")
    async def deviceinfo(self, ctx: BlooContext, device: Option(str, description="Name or board identifier", autocomplete=device_autocomplete, required=True)) -> None:
        """Fetches info of an Apple device

        Example usage
        -------------
        /deviceinfo device:<device>

        Parameters
        ----------
        device : str
            "Device identifier"
        """

        response = await get_ios_cfw()
        all_devices = response.get("groups")
        transformed_devices = transform_groups(all_devices)
        devices = [d for d in transformed_devices if d.get('name').lower() == device.lower(
        ) or device.lower() in [x.lower() for x in d.get('devices')]]

        if not devices:
            raise commands.BadArgument("No device found with that name.")

        matching_device_group = devices[0]

        embed = discord.Embed(title=matching_device_group.get(
            'name'), color=discord.Color.random())

        real = response.get("device")
        models = [
            real.get(dev) for dev in real if dev in matching_device_group.get("devices")]

        model_numbers = []
        model_names = ""
        for model_number in models:
            model_numbers.extend(model_number.get("model"))
            model_names += f"{model_number.get('name')} (`{model_number.get('identifier')}`)\n"

        model_numbers.sort()

        embed.add_field(name="Phones", value=model_names, inline=True)
        embed.add_field(
            name="SoC", value=f"{models[0].get('soc')} chip ({models[0].get('arch')})", inline=True)
        embed.add_field(name="Model(s)", value='`' +
                        "`, `".join(model_numbers) + "`", inline=False)
        embed.set_footer(text="Powered by https://ios.cfw.guide")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="View more on ios.cfw.guide",
                      url=f"https://ios.cfw.guide/chart/device/{matching_device_group.get('name').replace(' ', '-')}"))

        await ctx.respond(embed=embed, view=view, ephemeral=ctx.whisper)

    @whisper_in_general()
    @slash_command(guild_ids=[cfg.guild_id], description="Find out if you can jailbreak your device!")
    async def canijailbreak(self, ctx: BlooContext, device: Option(str, autocomplete=device_autocomplete_jb, description="Name or board identifier of the device"), version: Option(str, autocomplete=ios_on_device_autocomplete, description="Device OS version")) -> None:
        """Find out if you can jailbreak your device!

        Example usage
        -------------
        /canijailbreak device:<device> version:<version>

        Parameters
        ----------
        device : str
            "Device identifier"
        version : str
            "version identifier"
        """

        response = await get_ios_cfw()
        all_devices = response.get("device")
        device_groups = response.get("groups")

        transformed_groups = transform_groups(device_groups)
        devices = [group for group in transformed_groups if group.get(
            'name').lower() == device.lower() or device.lower() in [x.lower() for x in group.get('devices')]]

        if not devices:
            raise commands.BadArgument("No device found with that name.")

        device = devices[0].get("devices")[0]
        matching_device = all_devices.get(device)

        ios = response.get("ios")
        ios = [v for v in ios if device in v.get(
            'devices') and version == v.get('version')]

        if not ios:
            raise commands.BadArgument("No firmware found with that version.")

        matching_ios = ios[0]

        found_jbs = []

        jailbreaks = response.get("jailbreak")
        for jb in jailbreaks:
            if jb.get("compatibility") is None:
                continue

            for jb_version in jb.get("compatibility"):
                if matching_device.get("identifier") in jb_version.get("devices") and matching_ios.get("build") in jb_version.get("firmwares"):
                    found_jbs.append(jb)
                    break

        if not found_jbs:
            embed = discord.Embed(
                description=f"Sorry, **{matching_device.get('name')}** is not jailbreakable on **{matching_ios.get('version')}**.", color=discord.Color.red())
            await ctx.respond_or_edit(embed=embed, ephemeral=ctx.whisper)
        else:
            ctx.device = matching_device.get("name")
            ctx.device_id = matching_device.get("identifier")
            ctx.version = matching_ios.get("version")
            ctx.build = matching_ios.get("build")

            if len(found_jbs) > 0:
                found_jbs.sort(key=lambda x: str(
                    x.get("priority")) or x.get("name"))

            menu = CIJMenu(pages=found_jbs, channel=ctx.channel,
                           format_page=format_jailbreak_page, interaction=True, ctx=ctx, no_skip=True, whisper=ctx.whisper)

            await menu.start()

    @canijailbreak.error
    @deviceinfo.error
    @firmware.error
    @betafirmware.error
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
