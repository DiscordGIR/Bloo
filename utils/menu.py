import json

import aiohttp
import discord
from aiocache.decorators import cached

from utils.context import BlooContext, PromptData
from utils.views.menu import Menu


class TweakMenu(Menu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, timeout_function=self.on_timeout)
        self.jump_button = JumpButton(self.ctx.bot, len(self.pages), self)
        self.extra_buttons = []

    def refresh_button_state(self):
        if self.ctx.repo:
            extra_buttons = [
                discord.ui.Button(label='Add Repo to Sileo', emoji="<:sileo:679466569407004684>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={self.ctx.repo}', style=discord.ButtonStyle.url, row=1),
                discord.ui.Button(label='Add Repo to Zebra', emoji="<:zebra:911433583032422420>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={self.ctx.repo}', style=discord.ButtonStyle.url, row=1)
            ]
        else:
            extra_buttons = [
                discord.ui.Button(label='Cannot add default repo', emoji="<:sileo:679466569407004684>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={self.ctx.repo}', disabled=True, style=discord.ButtonStyle.url, row=1),
                discord.ui.Button(label='Cannot add default repo', emoji="🦓",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={self.ctx.repo}', disabled=True, style=discord.ButtonStyle.url, row=1)
            ]
        if self.ctx.depiction:
            extra_buttons.insert(0,
                                 discord.ui.Button(label='View Depiction', emoji="🔎",
                                                   url=self.ctx.depiction, style=discord.ButtonStyle.url, row=1),
                                 )

        if len(self.pages) > 1:
            extra_buttons.append(self.jump_button)

        for button in self.extra_buttons:
            self.remove_item(button)

        for button in extra_buttons:
            self.add_item(button)

        self.extra_buttons = extra_buttons

        super().refresh_button_state()

    async def on_timeout(self):
        self.jump_button.disabled = True
        self.stopped = True
        await self.refresh_response_message()
        self.stop()


class JumpButton(discord.ui.Button):
    def __init__(self, bot, max_page: int, tmb):
        super().__init__(style=discord.ButtonStyle.primary, emoji="⤴️")
        self.max_page = max_page
        self.bot = bot
        self.tmb = tmb
        self.row = 2

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.tmb.ctx.author:
            return

        ctx = await self.bot.get_application_context(interaction, cls=BlooContext)

        await interaction.response.defer(ephemeral=True)
        prompt = PromptData(
            value_name="page",
            description="What page do you want to jump to?",
            timeout=10,
            convertor=None)

        res = await ctx.prompt(prompt)
        if res is None:
            await ctx.send_warning("Cancelled")
            return

        try:
            res = int(res)
        except ValueError:
            await ctx.send_warning("Invalid page number!")
            return

        if res < 0 or res > self.max_page:
            await ctx.send_warning("Invalid page number!")
            return

        self.tmb.current_page = 1
        await self.tmb.refresh_response_message()
        await ctx.send_success(f"Jumped to page {res}!")


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


class CIJMenu(Menu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_buttons = []

    def refresh_button_state(self):
        extra_buttons = []
        if self.ctx.jb_info.get("website") is not None:
            extra_buttons.append(discord.ui.Button(label='Website', url=self.ctx.jb_info.get(
                "website").get("url"), style=discord.ButtonStyle.url, row=1))

        if self.ctx.jb_info.get('guide'):
            added = False
            for guide in self.ctx.jb_info.get('guide')[1:]:
                if self.ctx.build in guide.get("firmwares") and self.ctx.device_id in guide.get("devices"):
                    extra_buttons.append(discord.ui.Button(
                        label=f'{guide.get("name")} Guide', url=f"https://ios.cfw.guide{guide.get('url')}", style=discord.ButtonStyle.url, row=1))
                    added = True
                    break

            if not added:
                guide = self.ctx.jb_info.get('guide')[0]
                extra_buttons.append(discord.ui.Button(
                    label=f'{guide.get("name")} Guide', url=f"https://ios.cfw.guide{guide.get('url')}", style=discord.ButtonStyle.url, row=1))

        if self.ctx.jb_info.get("jailbreaksmeapp") is not None:
            if self.ctx.jba is None or self.ctx.signed.get('status') != 'Signed':
                extra_buttons.append(discord.ui.Button(label='Install with Jailbreaks.app',
                                                       url=f"https://api.jailbreaks.app/", style=discord.ButtonStyle.url, disabled=True, row=1))
            else:
                extra_buttons.append(discord.ui.Button(label='Install with Jailbreaks.app',
                                                       url=f"https://api.jailbreaks.app/install/{self.ctx.jba.get('name').replace(' ', '')}", style=discord.ButtonStyle.url, row=1))

        for button in self.extra_buttons:
            self.remove_item(button)

        for button in extra_buttons:
            self.add_item(button)

        self.extra_buttons = extra_buttons
        super().refresh_button_state()
