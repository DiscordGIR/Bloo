import time
import json
import aiohttp
import io
from colorthief import ColorThief

from discord.utils import format_dt
from discord.colour import Color
from discord.commands import slash_command
from discord.commands.commands import Option
from discord.embeds import Embed
from discord.ext import commands
from discord.member import Member
from utils.permissions import permissions
from utils.checks import PermissionsFailure, whisper
from utils.config import cfg
from utils.context import BlooContext
from utils.autocompleters.jailbreaks import apps_autocomplete
from utils.async_cache import async_cacher

@async_cacher()
async def get_apps():
    res_apps = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://jailbreaks.app/json/apps.json") as resp:
            if resp.status == 200:
                data = await resp.text()
                res_apps = json.loads(data)
    return res_apps

async def iterate_apps(query) -> dict:
    apps = await get_apps()
    for possibleApp in apps:
        if possibleApp['name'].lower() == query.lower():
            return possibleApp

class JailbreaksApp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.refreshTime = int(round(time.time() * 1000))

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info about an app.")
    async def app(self, ctx: BlooContext, name: Option(str, description="Name of the app", autocomplete=apps_autocomplete, required=True)) -> None:
        app = await iterate_apps(query=name)
        if app == None:
            await ctx.send_error("That app isn't on Jailbreaks.app.")
            return
        mainDLLink = f"https://api.jailbreaks.app/{name.replace(' ', '')}"
        allVersions = f"[Latest ({app['version']})](https://api.jailbreaks.app/{name.replace(' ', '')})"
        if len(app['other_versions']) != 0:
            for version in app['other_versions']:
                allVersions += f"\n[{version}](https://api.jailbreaks.app/{name.replace(' ', '')}/{version})"
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://jailbreaks.app/{app['icon']}") as icon:
                color = ColorThief(io.BytesIO(await icon.read())).get_color(quality=1)
        embed = Embed(title=app['name'], color=Color.from_rgb(color[0], color[1], color[2]), url=mainDLLink, description=app['short-description'])
        embed.set_thumbnail(url=f"https://jailbreaks.app/{app['icon']}")
        embed.add_field(name=f"Download{'' if len(app['other_versions']) == 0 else 's'}", value=allVersions, inline=True)
        embed.add_field(name="Developer", value=f"{('[' + app['dev'] + '](https://twitter.com/' + app['dev'] + ')') if app['dev'].startswith('@') else possibleApp['dev']}")
        embed.set_footer(text="Powered by Jailbreaks.app", icon_url="https://jailbreaks.app/img/Jailbreaks.png")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

def setup(bot):
    bot.add_cog(JailbreaksApp(bot))
