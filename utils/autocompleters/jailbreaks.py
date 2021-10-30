import json
import re

import aiohttp
from utils.async_cache import async_cacher


@async_cacher()
async def get_apps():
    res_apps = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://jailbreaks.app/json/apps.json") as resp:
            if resp.status == 200:
                data = await resp.text()
                apps = json.loads(data)

                # try to find an app with the name given in command
                for d in apps:
                    name = re.sub(r'\((.*?)\)', "", d["name"])
                    # get rid of '[ and ']'
                    name = name.replace('[', '')
                    name = name.replace(']', '')
                    name = name.strip()
                    if name not in res_apps:
                        res_apps.append(name)

    return res_apps


async def apps_autocomplete(_, value):
    apps = await get_apps()
    apps.sort()
    return [app for app in apps if app.lower().startswith(value.lower())][:25]
