import json
import re

import aiohttp
from utils.async_cache import async_cacher


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


async def device_autocomplete(_, value):
    devices = await get_devices()
    devices.sort()
    return [device for device in devices if device.lower().startswith(value.lower())][:25]
