import json
from typing import Callable, List

import aiohttp
import discord
from aiocache.decorators import cached

from utils.context import BlooContext
from utils.views.menu import MenuButtons


class Menu():
    def __init__(self, pages: list, channel: discord.TextChannel, format_page: Callable[[any, list, int, BlooContext], None], interaction: bool, ctx: BlooContext, whisper: bool = False, per_page=1, no_skip: bool = False, extra_buttons: List[discord.ui.Button] = []):
        # Declare variables that we need to use globally throughout the menu
        self.pages = pages
        self.channel = channel
        self.page_formatter = format_page
        self.is_interaction = interaction
        self.ctx = ctx
        self.should_whisper = whisper
        self.per_page = per_page
        self.no_skip = no_skip
        self.extra_buttons = extra_buttons

    async def start(self):
        """Initializes a menu"""
        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        self.pages = list(chunks(self.pages, self.per_page))

        # Prepare inital embed
        embed = await self.page_formatter(entries=self.pages[0], all_pages=self.pages, current_page=1, ctx=self.ctx)
        # Initialize our menu
        await MenuButtons(self.ctx, self.pages, self.page_formatter, self.channel, self.is_interaction, self.should_whisper, no_skip=self.no_skip, extra_buttons=self.extra_buttons).launch(embed)


class TweakMenu(Menu):
    def __init__(self, *args, **kwargs):
        # Declare variables that we need to use globally throughout the menu
        super().__init__(*args, **kwargs)

    async def start(self):
        """Initializes a menu"""
        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        self.pages = list(chunks(self.pages, self.per_page))

        # Prepare inital embed
        embed = await self.page_formatter(entries=self.pages[0], all_pages=self.pages, current_page=1, ctx=self.ctx)
        # Initialize our menu
        await TweakMenuButtons(self.ctx, self.pages, self.page_formatter, self.channel, self.is_interaction, self.should_whisper, no_skip=self.no_skip, extra_buttons=self.extra_buttons).launch(embed)


class TweakMenuButtons(MenuButtons):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def launch(self, embed):
        if self.ctx.repo:
            self.extra_buttons = [
                discord.ui.Button(label='Add Repo to Sileo', emoji="<:sileo:679466569407004684>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={self.ctx.repo}', style=discord.ButtonStyle.url),
                discord.ui.Button(label='Add Repo to Zebra', emoji="<:zebra:911433583032422420>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={self.ctx.repo}', style=discord.ButtonStyle.url)
            ]
        else:
            self.extra_buttons = [
                discord.ui.Button(label='Cannot add default repo', emoji="<:sileo:679466569407004684>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={self.ctx.repo}', disabled=True, style=discord.ButtonStyle.url),
                discord.ui.Button(label='Cannot add default repo', emoji="🦓",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={self.ctx.repo}', disabled=True, style=discord.ButtonStyle.url)
            ]

        await super().launch(embed)

    async def on_timeout(self):
        # Check if we even have any components enabled (if we don't, we don't need to do anything!)
        componentEnabled = False
        if 0 <= (self.array_current_page - 1) < len(self.pages):
            componentEnabled = True
        if len(self.pages) > self.current_page:
            componentEnabled = True
        if componentEnabled is False:
            return

        # Recursively disable all buttons
        for child in self.children:
            if child not in self.extra_buttons:
                child.disabled = True

        # If we aren't in an interaction, just edit the current message
        if self.is_interaction is False:
            await self.msg.edit(embed=self.embed, view=self)
        # Otherwise, handle with context
        else:
            if self.should_whisper is True:
                await self.ctx.respond_or_edit(embed=self.embed, view=self, ephemeral=True)
            else:
                await self.ctx.respond_or_edit(embed=self.embed, view=self)


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
        # Declare variables that we need to use globally throughout the menu
        super().__init__(*args, **kwargs)

    async def start(self):
        """Initializes a menu"""
        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        self.pages = list(chunks(self.pages, self.per_page))

        # Prepare inital embed
        embed = await self.page_formatter(entries=self.pages[0], all_pages=self.pages, current_page=1, ctx=self.ctx)

        await CIJMenuButtons(self.ctx, self.pages, self.page_formatter, self.channel, self.is_interaction, self.should_whisper, no_skip=self.no_skip, extra_buttons=self.extra_buttons).launch(embed)


class CIJMenuButtons(MenuButtons):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def launch(self, embed):
        self.extra_buttons = []
        if self.ctx.jb_info.get("website") is not None:
            self.extra_buttons.append(discord.ui.Button(label='Website', url=self.ctx.jb_info.get(
                "website").get("url"), style=discord.ButtonStyle.url))

        if self.ctx.jb_info.get('guide'):
            added = False
            for guide in self.ctx.jb_info.get('guide')[1:]:
                if self.ctx.build in guide.get("firmwares") and self.ctx.device_id in guide.get("devices"):
                    self.extra_buttons.append(discord.ui.Button(
                        label=f'{guide.get("name")} Guide', url=f"https://ios.cfw.guide{guide.get('url')}", style=discord.ButtonStyle.url))
                    added = True
                    break

            if not added:
                guide = self.ctx.jb_info.get('guide')[0]
                self.extra_buttons.append(discord.ui.Button(
                    label=f'{guide.get("name")} Guide', url=f"https://ios.cfw.guide{guide.get('url')}", style=discord.ButtonStyle.url))

        if self.ctx.jb_info.get("jailbreaksmeapp") is not None:
            jba = await iterate_apps(self.ctx.jb_info.get("name"))
            signed = await get_signed_status()
            if jba is None or signed.get('status') != 'Signed':
                self.extra_buttons.append(discord.ui.Button(label='Install with Jailbreaks.app',
                                                            url=f"https://api.jailbreaks.app/", style=discord.ButtonStyle.url, disabled=True))
            else:
                self.extra_buttons.append(discord.ui.Button(label='Install with Jailbreaks.app',
                                                            url=f"https://api.jailbreaks.app/install/{jba.get('name').replace(' ', '')}", style=discord.ButtonStyle.url))

        await super().launch(embed)

    async def on_timeout(self):
        # Check if we even have any components enabled (if we don't, we don't need to do anything!)
        componentEnabled = False
        if 0 <= (self.array_current_page - 1) < len(self.pages):
            componentEnabled = True
        if len(self.pages) > self.current_page:
            componentEnabled = True
        if componentEnabled is False:
            return

        # Recursively disable all buttons
        for child in self.children:
            if child not in self.extra_buttons:
                child.disabled = True

        # If we aren't in an interaction, just edit the current message
        if self.is_interaction is False:
            await self.msg.edit(embed=self.embed, view=self)
        # Otherwise, handle with context
        else:
            if self.should_whisper is True:
                await self.ctx.respond_or_edit(embed=self.embed, view=self, ephemeral=True)
            else:
                await self.ctx.respond_or_edit(embed=self.embed, view=self)
