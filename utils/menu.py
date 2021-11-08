import discord
from typing import Callable
from utils.context import BlooContext
from utils.views.menu import MenuButtons

class Menu():
    def __init__(self, pages: list, channel: discord.TextChannel, format_page: Callable[[any, list, int, BlooContext], None], interaction: bool, ctx: BlooContext, whisper: bool, **kwargs):
        # Declare variables that we need to use globally throughout the menu
        self.pages = pages
        self.channel = channel
        self.page_formatter = format_page
        self.is_interaction = interaction
        self.ctx = ctx
        self.should_whisper = whisper
        self.kwargs = kwargs

    async def init_menu(self):
        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        
        for key, value in self.kwargs.items():
            if key == "per_page":
                self.pages = list(chunks(self.pages, value))
        # Prepare inital embed
        embed = await self.page_formatter(entry=self.pages[0], all_pages=self.pages, current_page=1, ctx=self.ctx)
        # Initialize our menu
        await MenuButtons(self.ctx, self.pages, self.page_formatter, self.channel, self.is_interaction, self.should_whisper).launch(embed)