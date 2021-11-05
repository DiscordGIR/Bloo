from utils.context import BlooContext
from utils.views.menu import MenuButtons

class Menu():
    def __init__(self, pages, bot, channel, format_page, interaction: bool, ctx: BlooContext, whisper: bool):
        self.pages = pages
        self.bot = bot
        self.channel = channel
        self.page_formatter = format_page
        self.is_interaction = interaction
        self.ctx = ctx
        self.should_whisper = whisper

    async def init_menu(self):
        embed = await self.page_formatter(entry=self.pages[0], all_pages=self.pages, current_page=1)
        await MenuButtons(self.ctx, self.pages, self.page_formatter, self.channel, self.is_interaction, self.should_whisper).launch(embed)