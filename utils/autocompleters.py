import json
import re
from itertools import groupby

import aiohttp
from aiocache import cached
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands.context import AutocompleteContext

from utils.mod.give_birthday_role import MONTH_MAPPING


def sort_versions(version):
    v = version.split(' ')
    v[0] = list(map(int, v[0].split('.')))
    return v


def transform_groups(groups):
    final_groups = []
    for group in groups:
        if group.get("subgroups") is not None:
            for subgroup in group.get('subgroups'):
                subgroup['order'] = group.get('order')
                final_groups.append(subgroup)
        else:
            final_groups.append(group)

    return final_groups


@cached(ttl=3600)
async def get_devices_ipswme():
    res_devices = []
    seen_devices = set()
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
                    
                    
                    if name not in seen_devices:
                        d["name"] = name
                        res_devices.append(d)
                        seen_devices.add(name)

    return res_devices


@cached(ttl=3600)
async def find_firmwares_from_ipsw_me(identifier):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.ipsw.me/v4/device/{identifier}") as resp:
            if resp.status == 200:
                firmwares = json.loads(await resp.text())["firmwares"]
                firmwares = [firmware["version"] for firmware in firmwares]

    firmwares.sort(key=sort_versions, reverse=True)
    return firmwares


async def device_autocomplete_ipswme(ctx: AutocompleteContext):
    devices = await get_devices_ipswme()
    devices.sort(key=lambda x: x['name'].lower())
    return [device["name"] for device in devices if device["name"].lower().startswith(ctx.value.lower()) and device["name"].lower().split()[0] in ['iphone', 'ipod', 'ipad']][:25]


async def ios_on_device_autocomplete_ipswme(ctx: AutocompleteContext):
    device = ctx.options.get("device")
    all_devices = await get_devices_ipswme()
    device_final = [d["identifier"] for d in all_devices if device.lower() == d["name"].lower()]
    
    if not device_final:
        return []
    
    device_final = device_final[0]
    firmwares = await find_firmwares_from_ipsw_me(device_final)
    return firmwares[:25]
    

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


async def jb_autocomplete(ctx: AutocompleteContext):
    apps = await get_ios_cfw()
    if apps is None:
        return []

    apps = apps.get("jailbreak")
    apps.sort(key=lambda x: x["name"].lower())
    return [app["name"] for app in apps if app["name"].lower().startswith(ctx.value.lower())][:25]


async def ios_version_autocomplete(ctx: AutocompleteContext):
    versions = await get_ios_cfw()
    if versions is None:
        return []

    versions = versions.get("ios")
    versions.sort(key=lambda x: x.get("released")
                  or "1970-01-01", reverse=True)
    return [f"{v['version']} ({v['build']})" for v in versions if (ctx.value.lower() in v['version'].lower() or ctx.value.lower() in v['build'].lower()) and not v['beta']][:25]


async def ios_on_device_autocomplete(ctx: AutocompleteContext):
    cfw = await get_ios_cfw()
    if cfw is None:
        return []

    ios = cfw.get("ios")
    devices = cfw.get("groups")
    transformed_devices = transform_groups(devices)
    selected_device = ctx.options.get("device")

    matching_devices = [
        d for d in transformed_devices if selected_device.lower() == d.get('name').lower() or any(selected_device.lower() == x.lower() for x in d.get("devices"))]

    if not matching_devices:
        return []

    matching_device = matching_devices[0].get("devices")[0]
    matching_ios = [version.get("version") for version in ios if matching_device in version.get(
        'devices') and ctx.value.lower() in version.get('version').lower()]

    matching_ios.sort(key=sort_versions, reverse=True)
    return matching_ios[:25]


async def device_autocomplete(ctx: AutocompleteContext):
    res = await get_ios_cfw()
    if res is None:
        return []

    all_devices = res.get("groups")
    transformed_devices = transform_groups(all_devices)
    devices = [d for d in transformed_devices if (any(ctx.value.lower() in x.lower() for x in d.get('devices')) or ctx.value.lower() in d.get('name').lower())]

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


async def device_autocomplete_jb(ctx: AutocompleteContext):
    res = await get_ios_cfw()
    if res is None:
        return []

    all_devices = res.get("groups")
    transformed_devices = transform_groups(all_devices)
    devices = [d for d in transformed_devices if (any(ctx.value.lower() in x.lower() for x in d.get(
        'devices')) or ctx.value.lower() in d.get('name').lower()) and d.get('type') not in ["TV", "Watch"]]

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


async def ios_beta_version_autocomplete(ctx: AutocompleteContext):
    versions = await get_ios_cfw()
    if versions is None:
        return []

    versions = versions.get("ios")
    versions.sort(key=lambda x: x.get("released")
                  or "1970-01-01", reverse=True)
    return [f"{v['version']} ({v['build']})" for v in versions if (ctx.value.lower() in v['version'].lower() or ctx.value.lower() in v['build'].lower()) and v['beta']][:25]


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
