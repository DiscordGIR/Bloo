from discord.commands.context import AutocompleteContext
import json
import re
import aiohttp
from utils.async_cache import async_cacher

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
