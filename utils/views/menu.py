from discord import ButtonStyle, Interaction, SelectOption, ui
from utils.context import BlooContext

class MenuButtons(ui.View):
    def __init__(self, ctx, pages, page_formatter, channel, interaction: bool, whisper: bool):
        super().__init__()
        self.channel = channel
        self.is_interaction = interaction
        self.should_whisper = whisper
        self.current_page = 1
        self.array_current_page = 0
        self.pages = pages
        self.page_formatter = page_formatter
        self.ctx = ctx
        self.msg = None
        
    async def launch(self, embed):
        self.previous.disabled = True
        self.next.disabled = True
        componentEnabled = False
        if 0 <= (self.array_current_page - 1) < len(self.pages):
            self.previous.disabled = False
            componentEnabled = True
        if len(self.pages) > self.current_page:
            self.next.disabled = False
            componentEnabled = True
            
        if self.is_interaction is False:
            if self.msg is None:
                if componentEnabled is True:
                    self.msg = await self.channel.send(embed=embed, view=self)
                else:
                    self.msg = await self.channel.send(embed=embed)
            else:
                if componentEnabled is True:
                    await self.msg.edit(embed=embed, view=self)
                else:
                    await self.msg.edit(embed=embed)
        else:
            if componentEnabled is True:
                await self.ctx.respond_or_edit(embed=embed, view=self, ephemeral=self.should_whisper)
            else:
                await self.ctx.respond_or_edit(embed=embed, ephemeral=self.should_whisper)
    
    @ui.button(emoji='⬅️', style=ButtonStyle.blurple, row=1, disabled=True)
    async def previous(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            self.array_current_page = (self.array_current_page - 1)
            self.current_page = (self.current_page - 1)
            embed = await self.page_formatter(entry=self.pages[self.array_current_page], all_pages=self.pages, current_page=self.current_page)
            await self.launch(embed)
            
    @ui.button(emoji='➡️', style=ButtonStyle.blurple, row=1, disabled=True)
    async def next(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            self.array_current_page = (self.array_current_page + 1)
            self.current_page = (self.current_page + 1)
            embed = await self.page_formatter(entry=self.pages[self.array_current_page], all_pages=self.pages, current_page=self.current_page)
            await self.launch(embed)