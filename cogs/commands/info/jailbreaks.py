import discord
from discord.commands import slash_command, Option
from discord.ext import commands
import time
import json
import aiohttp
import io
import logging
from colorthief import ColorThief
from utils.permissions.checks import whisper
from utils.config import cfg
from utils.database import Guild
from utils.context import BlooContext
from utils.autocompleters.jailbreaks import jb_autocomplete
from utils.async_cache import async_cacher
from utils.permissions.permissions import permissions

@async_cacher()
async def get_jailbreaks_jba():
    res_apps = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://jailbreaks.app/json/apps.json") as resp:
            if resp.status == 200:
                data = await resp.text()
                res_apps = json.loads(data)
    return res_apps

@async_cacher()
async def get_jailbreaks():
    response = {}
    async with aiohttp.ClientSession() as client:
        async with client.get('https://assets.stkc.win/jailbreaks.json') as resp:
            if resp.status == 200:
                data = await resp.text()
                response = json.loads(data)
    return response

async def iterate_apps(query) -> dict:
    apps = await get_jailbreaks_jba()
    for possibleApp in apps:
        if possibleApp.get('name').lower() == query.lower().replace("œ", "oe"):
            return possibleApp

class Jailbreak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.refreshTime = int(round(time.time() * 1000))

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info about a jailbreak.")
    async def jailbreak(self, ctx: BlooContext, name: Option(str, description="Name of the jailbreak", autocomplete=jb_autocomplete, required=True), whisper: Option(bool, description="Whisper? (No by default)", required=False)) -> None:
        should_whisper = False
        if not permissions.has(ctx.guild, ctx.author, 5) and ctx.channel.id == Guild.channel_general:
            should_whisper = True
        else:
            should_whisper = whisper
        response = await get_jailbreaks()
        try:
            for object in response[f'{name.lower().replace("œ", "oe")}']:
                view = None
                embed = discord.Embed(title=object['Name'], color=discord.Color.random())
                embed.add_field(name="Version", value=object['LatestVersion'], inline=True)
                embed.add_field(name="Compatible with", value=object['Versions'], inline=True)
                embed.add_field(name="Type", value=object['Type'], inline=False)
                embed.add_field(name="Website", value=object['Website'], inline=False)
                if object.get('Guide') is not None:
                    embed.add_field(name="Guide", value=object['Guide'], inline=False)
                if object.get('Notes') is not None:
                    embed.add_field(name="Notes", value=object['Notes'], inline=False)
                jba = await iterate_apps(object.get('Name'))
                if jba is not None:
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label='Install with Jailbreaks.app', url=f"https://api.jailbreaks.app/install/{jba.get('name').replace(' ', '')}", style=discord.ButtonStyle.url))
                if object.get('Icon') is not None:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(object.get('Icon')) as icon:
                            color = ColorThief(io.BytesIO(await icon.read())).get_color(quality=1)
                            embed.color = discord.Color.from_rgb(color[0], color[1], color[2])
                    embed.set_thumbnail(url=object.get('Icon'))
                if view is not None:
                    await ctx.respond_or_edit(embed=embed, ephemeral=should_whisper, view=view)
                else:
                    await ctx.respond_or_edit(embed=embed, ephemeral=should_whisper)
        except:
            logging.exception('')
            await ctx.send_error("Sorry, I couldn't find any jailbreaks with that name.")

def setup(bot):
    bot.add_cog(Jailbreak(bot))
