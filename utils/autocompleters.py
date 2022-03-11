import json
import re
from itertools import groupby
from typing import List

import aiohttp
from aiocache import cached
import discord
from discord.commands import OptionChoice
from data.model.case import Case
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands.context import AutocompleteContext

from utils.mod.give_birthday_role import MONTH_MAPPING


def sort_versions(version):
    v = version.split(' ')
    v[0] = list(map(int, v[1].split('.')))
    return v


def transform_groups(groups):
    final_groups = []
    groups = [g for _, g in groups.items()]
    for group in groups:
        if group.get("subgroup") is not None:
            for subgroup in group.get("subgroup"):
                subgroup["order"] = group.get("order")
                final_groups.append(subgroup)
        else:
            final_groups.append(group)

    return final_groups


@cached(ttl=3600)
async def get_ios_cfw():
    """Gets all apps on ios.cfw.guide

    Returns
    -------
    dict
        "ios, jailbreaks, devices"
    """

    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.appledb.dev/main.json") as resp:
            if resp.status == 200:
                data = await resp.json()

    return data


async def bypass_autocomplete(ctx: AutocompleteContext):
    data = await get_ios_cfw()
    bypasses = data.get("bypass")
    apps = [b.get("name") for _, b in bypasses.items()]
    apps.sort(key=lambda x: x.lower())
    return [app for app in apps if ctx.value.lower() in app.lower()][:25]


async def jb_autocomplete(ctx: AutocompleteContext):
    apps = await get_ios_cfw()
    if apps is None:
        return []

    apps = apps.get("jailbreak")
    apps = [jb for _, jb in apps.items()]
    apps.sort(key=lambda x: x["name"].lower())
    return [app["name"] for app in apps if app["name"].lower().startswith(ctx.value.lower())][:25]


async def ios_version_autocomplete(ctx: AutocompleteContext):
    versions = await get_ios_cfw()
    if versions is None:
        return []

    versions = versions.get("ios")
    versions = [v for _, v in versions.items()]
    versions.sort(key=lambda x: x.get("released")
                  or "1970-01-01", reverse=True)
    return [f"{v['osStr']} {v['version']} ({v['build']})" for v in versions if (ctx.value.lower() in v['version'].lower() or ctx.value.lower() in v['build'].lower()) and not v['beta']][:25]


async def ios_beta_version_autocomplete(ctx: AutocompleteContext):
    versions = await get_ios_cfw()
    if versions is None:
        return []

    versions = versions.get("ios")
    versions = [v for _, v in versions.items()]
    versions.sort(key=lambda x: x.get("released")
                  or "1970-01-01", reverse=True)
    return [f"{v['osStr']} {v['version']} ({v['build']})" for v in versions if (ctx.value.lower() in v['version'].lower() or ctx.value.lower() in v['build'].lower()) and v['beta']][:25]


async def ios_on_device_autocomplete(ctx: AutocompleteContext):
    cfw = await get_ios_cfw()
    if cfw is None:
        return []

    ios = cfw.get("ios")
    ios = [i for _, i in ios.items()]
    devices = cfw.get("group")
    transformed_devices = transform_groups(devices)
    selected_device = ctx.options.get("device")

    if selected_device is None:
        return []
    matching_devices = [
        d for d in transformed_devices if selected_device.lower() == d.get('name').lower() or any(selected_device.lower() == x.lower() for x in d.get("devices"))]

    if not matching_devices:
        return []

    matching_device = matching_devices[0].get("devices")[0]
    matching_ios = [f'{version.get("osStr")} {version.get("version")}' for version in ios if matching_device in version.get(
        'devices') and ctx.value.lower() in version.get('version').lower()]

    matching_ios.sort(key=sort_versions, reverse=True)
    return matching_ios[:25]


async def device_autocomplete(ctx: AutocompleteContext):
    res = await get_ios_cfw()
    if res is None:
        return []

    all_devices = res.get("group")
    transformed_devices = transform_groups(all_devices)
    devices = [d for d in transformed_devices if (any(ctx.value.lower() in x.lower(
    ) for x in d.get('devices')) or ctx.value.lower() in d.get('name').lower())]

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

    all_devices = res.get("group")
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


async def date_autocompleter(ctx: AutocompleteContext) -> list:
    """Autocompletes the date parameter for !mybirthday"""
    month = MONTH_MAPPING.get(ctx.options.get("month"))
    if month is None:
        return []

    return [i for i in range(1, month["max_days"]+1) if str(i).startswith(str(ctx.value))][:25]


async def tags_autocomplete(ctx: AutocompleteContext):
    tags = [tag.name.lower() for tag in guild_service.get_guild().tags]
    tags.sort()
    return [tag for tag in tags if ctx.value.lower() in tag.lower()][:25]


async def memes_autocomplete(ctx: AutocompleteContext):
    memes = [meme.name.lower() for meme in guild_service.get_guild().memes]
    memes.sort()
    return [meme for meme in memes if ctx.value.lower() in meme.lower()][:25]


async def liftwarn_autocomplete(ctx: AutocompleteContext):
    cases: List[Case] = [case for case in user_service.get_cases(
        int(ctx.options["user"])).cases if case._type == "WARN" and not case.lifted]
    cases.sort(key=lambda x: x._id, reverse=True)

    return [OptionChoice(f"{case._id} - {case.punishment} points - {case.reason}", str(case._id)) for case in cases if (not ctx.value or str(case._id).startswith(str(ctx.value)))][:25]


async def filterwords_autocomplete(ctx: AutocompleteContext):
    words = [word.word for word in guild_service.get_guild().filter_words]
    words.sort()

    return [word for word in words if str(word).startswith(str(ctx.value))][:25]


async def issue_autocomplete(ctx: AutocompleteContext):
    issue_titles = [issue for issue in ctx.bot.issue_cache.cache]
    issue_titles.sort(key=lambda issue: issue.lower())

    return [issue_title for issue_title in issue_titles if ctx.value.lower() in issue_title.lower()][:25]


async def rule_autocomplete(ctx: AutocompleteContext):
    rule_titles = [(issue, ctx.bot.rule_cache.cache[issue].description) for issue in ctx.bot.rule_cache.cache]
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key[0])]
    rule_titles.sort(key=alphanum_key)
    return [OptionChoice(f"{title} - {description}"[:100], title) for title, description in rule_titles if ctx.value.lower() in title.lower() or ctx.value.lower() in description.lower()][:25]


@cached(ttl=3600)
async def fetch_repos():
    async with aiohttp.ClientSession() as client:
        async with client.get('https://api.canister.me/v1/community/repositories/search?ranking=1,2,3,4,5') as resp:
            if resp.status == 200:
                response = await resp.json(content_type=None)
                return response.get("data")

            return None


async def repo_autocomplete(ctx: AutocompleteContext):
    repos = await fetch_repos()
    if repos is None:
        return []
    repos = [repo['slug'] for repo in repos if repo.get(
        "slug") and repo.get("slug") is not None]
    repos.sort()
    return [repo for repo in repos if ctx.value.lower() in repo.lower()][:25]


async def commands_list(ctx: AutocompleteContext):
    res = []
    for cog in ctx.bot.cogs:
        for command in ctx.bot.cogs[cog].get_commands():
            if isinstance(command, discord.MessageCommand) or isinstance(command, discord.UserCommand):
                continue
            elif isinstance(command, discord.SlashCommandGroup):
                for sub_command in command.subcommands:
                    if ctx.value.lower() in f"{command.name} {sub_command.name}":
                        res.append(f"{command.name} {sub_command.name}")
            else:
                if ctx.value.lower() in command.name:
                    res.append(command.name.lower())

    res.sort()
    return res

async def command_names_list(ctx: AutocompleteContext):
    res = []
    for cog in ctx.bot.cogs:
        for command in ctx.bot.cogs[cog].get_commands():
            if isinstance(command, discord.MessageCommand) or isinstance(command, discord.UserCommand):
                continue
            else:
                if ctx.value.lower() in command.name:
                    res.append(command.name.lower())

    res.sort()
    return res