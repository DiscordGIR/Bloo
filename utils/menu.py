import discord

from typing import Callable, List
from utils.context import BlooContext
from utils.views.menu import MenuButtons

class Menu():
    def __init__(self, pages: list, channel: discord.TextChannel, format_page: Callable[[any, list, int, BlooContext], None], interaction: bool, ctx: BlooContext, whisper: bool=False, per_page=1, no_skip: bool = False, extra_buttons: List[discord.ui.Button] = []):
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
        if self.ctx.repo:
            self.extra_buttons = [
                discord.ui.Button(label='Add Repo to Sileo', emoji="<:sileo:679466569407004684>", url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={self.ctx.repo}', style=discord.ButtonStyle.url),
                discord.ui.Button(label='Add Repo to Zebra', emoji="<:zebra:911433583032422420>", url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={self.ctx.repo}', style=discord.ButtonStyle.url)
            ]
        else:
            self.extra_buttons = [
                discord.ui.Button(label='Cannot add default repo', emoji="<:sileo:679466569407004684>", url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={self.ctx.repo}', disabled=True, style=discord.ButtonStyle.url),
                discord.ui.Button(label='Cannot add default repo', emoji="🦓", url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={self.ctx.repo}', disabled=True, style=discord.ButtonStyle.url)
            ]

        await TweakMenuButtons(self.ctx, self.pages, self.page_formatter, self.channel, self.is_interaction, self.should_whisper, no_skip=self.no_skip, extra_buttons=self.extra_buttons).launch(embed)


class TweakMenuButtons(MenuButtons):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    async def launch(self, embed):
        if self.ctx.repo:
            self.extra_buttons = [
                discord.ui.Button(label='Add Repo to Sileo', emoji="<:sileo:679466569407004684>", url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={self.ctx.repo}', style=discord.ButtonStyle.url),
                discord.ui.Button(label='Add Repo to Zebra', emoji="🦓", url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={self.ctx.repo}', style=discord.ButtonStyle.url)
            ]
        else:
            self.extra_buttons = [
                discord.ui.Button(label='Cannot add default repo', emoji="<:sileo:679466569407004684>", url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={self.ctx.repo}', disabled=True, style=discord.ButtonStyle.url),
                discord.ui.Button(label='Cannot add default repo', emoji="🦓", url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={self.ctx.repo}', disabled=True, style=discord.ButtonStyle.url)
            ]
        
        await super().launch(embed)