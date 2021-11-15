import json
import re

import aiohttp
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands.context import AutocompleteContext

from utils.async_cache import async_cacher
from utils.mod.give_birthday_role import MONTH_MAPPING


@async_cacher()
async def get_devices():
    res_devices = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.ipsw.me/v4/devices") as resp:
            if resp.status == 200:
                data = await resp.text()
                devices = json.loads(data)
                devices.append(
                    {'name': 'iPhone SE 2', 'identifier': 'iPhone12,8'})

                # try to find a device with the name given in command
                for d in devices:
                    # remove regional version info of device i.e iPhone SE (CDMA) -> iPhone SE
                    name = re.sub(r'\((.*?)\)', "", d["name"])
                    # get rid of '[ and ']'
                    name = name.replace('[', '')
                    name = name.replace(']', '')
                    name = name.strip()
                    if name not in res_devices:
                        res_devices.append(name)

    return res_devices


async def device_autocomplete(ctx: AutocompleteContext):
    devices = await get_devices()
    devices.sort()
    return [device for device in devices if device.lower().startswith(ctx.value.lower())][:25]


@async_cacher()
async def get_jailbreaks():
    res_apps = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://assets.stkc.win/jailbreaks.json") as resp:
            if resp.status == 200:
                data = await resp.text()
                jailbreaks = json.loads(data)

                # try to find an app with the name given in command
                for d in jailbreaks:
                    jb = jailbreaks[d][0]
                    name = re.sub(r'\((.*?)\)', "", jb["Name"])
                    # get rid of '[ and ']'
                    name = name.replace('[', '')
                    name = name.replace(']', '')
                    name = name.strip()
                    if name not in res_apps:
                        res_apps.append(name)

    return res_apps


async def jb_autocomplete(ctx: AutocompleteContext):
    apps = await get_jailbreaks()
    apps.sort()
    return [app for app in apps if app.lower().startswith(ctx.value.lower())][:25]


async def date_autocompleter(ctx: AutocompleteContext) -> list:
    """Autocompletes the date parameter for !mybirthday"""
    month = MONTH_MAPPING.get(ctx.options.get("month"))
    if month is None:
        return []

    return [i for i in range(1, month["max_days"]+1) if str(ctx.value) in str(i)][:25]


async def tags_autocomplete(ctx: AutocompleteContext):
    tags = [tag.name.lower() for tag in guild_service.get_guild().tags]
    tags.sort()
    tags = tags[:25]
    return [tag for tag in tags if tag.lower().startswith(ctx.value.lower())]


async def liftwarn_autocomplete(ctx: AutocompleteContext):
    cases = [case._id for case in user_service.get_cases(
        int(ctx.options["user"])).cases if case._type == "WARN" and not case.lifted]
    cases.sort(reverse=True)
    cases = cases[:25]

    return [case for case in cases if str(case).startswith(str(ctx.value))]


async def filterwords_autocomplete(ctx: AutocompleteContext):
    words = [word.word for word in guild_service.get_guild().filter_words]
    words.sort()
    words = words[:25]

    return [word for word in words if str(word).startswith(str(ctx.value))]
