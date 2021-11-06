from utils.context import BlooContext
from utils.views.menu import MenuButtons

class Menu():
    def __init__(self, pages: list, channel, format_page, interaction: bool, ctx: BlooContext, whisper: bool):
        # Declare variables that we need to use globally throughout the menu
        self.pages = pages
        self.channel = channel
        self.page_formatter = format_page
        self.is_interaction = interaction
        self.ctx = ctx
        self.should_whisper = whisper

    async def init_menu(self):
        # Prepare inital embed
        embed = await self.page_formatter(entry=self.pages[0], all_pages=self.pages, current_page=1)
        # Initialize our menu
        await MenuButtons(self.ctx, self.pages, self.page_formatter, self.channel, self.is_interaction, self.should_whisper).launch(embed)