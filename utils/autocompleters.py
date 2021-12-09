from itertools import chain, groupby
import json
import re

import aiohttp
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands.context import AutocompleteContext

from aiocache import cached
from utils.mod.give_birthday_role import MONTH_MAPPING


@cached(ttl=3600)
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
    return [device for device in devices if device.lower().startswith(ctx.value.lower()) and device.lower().split()[0] in ['iphone', 'ipod', 'ipad', 'homepod', 'apple']][:25]


@cached(ttl=3600)
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

@cached(ttl=3600)
async def get_ios_cfw():
    """Gets all apps on ios.cfw.guide

    Returns
    -------
    dict
        "ios, jailbreaks, devices"
    """

    async with aiohttp.ClientSession() as session:
        # async with session.get("https://ios.cfw.guide/main.json") as resp:
        async with session.get("https://cdn.discordapp.com/attachments/846383888862937183/918382158601670666/main.json") as resp:
            if resp.status == 200:
                data = await resp.json()

    return data


async def jb_autocomplete(ctx: AutocompleteContext):
    apps = await get_ios_cfw()
    if apps is None:
        return []

    apps = apps.get("jailbreak")
    apps.sort(key=lambda x: x["name"].lower())
    return [app["name"] for app in apps if app["name"].lower().startswith(ctx.value.lower())][:25]


async def ios_autocomplete(ctx: AutocompleteContext):
    versions = await get_ios_cfw()
    if versions is None:
        return []
    
    versions = versions.get("ios")
    versions.sort(key=lambda x: x.get("released") or "1970-01-01", reverse=True)
    return [f"{v['version']} ({v['build']})" for v in versions if (ctx.value.lower() in v['version'].lower() or ctx.value.lower() in v['build'].lower()) and not v['beta']][:25]


async def verison_jb_autocomplete(ctx: AutocompleteContext):
    cfw = await get_ios_cfw()
    if cfw is None:
        return []
    
    ios = cfw.get("ios")
    devices = cfw.get("device")
    selected_device = ctx.options.get("device")

    matching_devices = [d for d in devices if d.lower() == selected_device.lower() or devices.get(d).get('name').lower() == selected_device.lower()]
    if not matching_devices:
        return []
    
    matching_device = matching_devices[0]
    matching_ios = [version.get("version") for version in ios if matching_device in version.get('devices')]
    matching_ios.sort(reverse=True)
    return matching_ios[:25]

async def ios_beta_autocomplete(ctx: AutocompleteContext):
    versions = await get_ios_cfw()
    if versions is None:
        return []
    
    versions = versions.get("ios")
    versions.sort(key=lambda x: x.get("released") or "1970-01-01", reverse=True)
    return [f"{v['version']} ({v['build']})" for v in versions if (ctx.value.lower() in v['version'].lower() or ctx.value.lower() in v['build'].lower()) and v['beta']][:25]


async def device_autocomplete(ctx: AutocompleteContext):
    res = await get_ios_cfw()
    if res is None:
        return []
    
    devices = res.get("groups")
    devices = [d for d in devices if ctx.value.lower() in [in_device.lower() for in_device in d.get('devices')] or ctx.value.lower() in d.get('name').lower()]

    devices.sort(key=lambda x: x.get('type') or "zzz")
    devices_groups = groupby(devices, lambda x: x.get('type'))
    
    devices = []
    for _, group in devices_groups:
        group = list(group)
        group.sort(key=lambda x: x.get('order'), reverse=True)
        devices.extend(group)
        
        if len(devices) >= 25:
            break

    return [device.get('name') for device in devices][:25]


async def date_autocompleter(ctx: AutocompleteContext) -> list:
    """Autocompletes the date parameter for !mybirthday"""
    month = MONTH_MAPPING.get(ctx.options.get("month"))
    if month is None:
        return []

    return [i for i in range(1, month["max_days"]+1) if str(i).startswith(str(ctx.value))][:25]


async def tags_autocomplete(ctx: AutocompleteContext):
    tags = [tag.name.lower() for tag in guild_service.get_guild().tags]
    tags.sort()
    return [tag for tag in tags if tag.lower().startswith(ctx.value.lower())][:25]

async def memes_autocomplete(ctx: AutocompleteContext):
    memes = [meme.name.lower() for meme in guild_service.get_guild().memes]
    memes.sort()
    return [meme for meme in memes if meme.lower().startswith(ctx.value.lower())][:25]


async def liftwarn_autocomplete(ctx: AutocompleteContext):
    cases = [case._id for case in user_service.get_cases(
        int(ctx.options["user"])).cases if case._type == "WARN" and not case.lifted]
    cases.sort(reverse=True)

    return [case for case in cases if str(case).startswith(str(ctx.value))][:25]


async def filterwords_autocomplete(ctx: AutocompleteContext):
    words = [word.word for word in guild_service.get_guild().filter_words]
    words.sort()

    return [word for word in words if str(word).startswith(str(ctx.value))][:25]
