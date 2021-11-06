from discord import ButtonStyle, Interaction, ui
from utils.context import BlooContext
from discord.channel import TextChannel

class MenuButtons(ui.View):
    def __init__(self, ctx: BlooContext, pages: list, page_formatter, channel: TextChannel, interaction: bool, whisper: bool):
        super().__init__(timeout=60)
        self.channel = channel
        self.is_interaction = interaction
        self.should_whisper = whisper
        self.current_page = 1
        self.array_current_page = 0
        self.pages = pages
        self.page_formatter = page_formatter
        self.ctx = ctx
        self.msg = None
        self.embed = None
        
    async def launch(self, embed):
        self.embed = embed
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
                if self.should_whisper is True:
                    await self.ctx.respond_or_edit(embed=embed, view=self, ephemeral=True)
                else:
                    await self.ctx.respond_or_edit(embed=embed, view=self)
            else:
                if self.should_whisper is True:
                    await self.ctx.respond_or_edit(embed=embed, ephemeral=True)
                else:
                    await self.ctx.respond_or_edit(embed=embed)
    
    @ui.button(emoji='⬅️', style=ButtonStyle.blurple, row=1, disabled=True)
    async def previous(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            self.array_current_page = (self.array_current_page - 1)
            self.current_page = (self.current_page - 1)
            embed = await self.page_formatter(entry=self.pages[self.array_current_page], all_pages=self.pages, current_page=self.current_page)
            await self.launch(embed)
            
    @ui.button(emoji='⏹️', style=ButtonStyle.blurple, row=1)
    async def pause(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            await self.on_timeout()
            
    @ui.button(emoji='➡️', style=ButtonStyle.blurple, row=1, disabled=True)
    async def next(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            self.array_current_page = (self.array_current_page + 1)
            self.current_page = (self.current_page + 1)
            embed = await self.page_formatter(entry=self.pages[self.array_current_page], all_pages=self.pages, current_page=self.current_page)
            await self.launch(embed)

    async def on_timeout(self):
        componentEnabled = False
        if 0 <= (self.array_current_page - 1) < len(self.pages):
            componentEnabled = True
        if len(self.pages) > self.current_page:
            componentEnabled = True
        if componentEnabled is False:
            return
        for child in self.children:
            child.disabled = True
        if self.is_interaction is False:
            await self.msg.edit(embed=self.embed, view=self)
        else:
            if self.should_whisper is True:
                await self.ctx.respond_or_edit(embed=self.embed, view=self, ephemeral=True)
            else:
                await self.ctx.respond_or_edit(embed=self.embed, view=self)