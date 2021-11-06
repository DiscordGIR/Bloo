from discord import ButtonStyle, Interaction, ui
from utils.context import BlooContext
from discord.channel import TextChannel

class MenuButtons(ui.View):
    def __init__(self, ctx: BlooContext, pages: list, page_formatter, channel: TextChannel, interaction: bool, whisper: bool):
        # Tell buttons to disable after 60 seconds
        super().__init__(timeout=60)
        # Declare variables that we need to use globally throughout the menu
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
        # See which buttons we actually need enabled
        self.first.disabled = True
        self.last.disabled = True
        if len(self.pages) > 1:
            if self.current_page != len(self.pages):
                self.last.disabled = False
            if self.array_current_page != 0:
                self.first.disabled = False
        self.previous.disabled = True
        self.next.disabled = True
        componentEnabled = False
        if 0 <= (self.array_current_page - 1) < len(self.pages):
            self.previous.disabled = False
            componentEnabled = True
        if len(self.pages) > self.current_page:
            self.next.disabled = False
            componentEnabled = True
        
        # If we aren't in an interaction,
        if self.is_interaction is False:
            if self.msg is None:
                # This is so we don't have buttons needlessly enabled for tweaks with only 1 page
                if componentEnabled is True:
                    self.msg = await self.channel.send(embed=embed, view=self)
                else:
                    self.msg = await self.channel.send(embed=embed)
            else:
                if componentEnabled is True:
                    await self.msg.edit(embed=embed, view=self)
                else:
                    await self.msg.edit(embed=embed)
        # Otherwise,
        else:
            # Handle for an interaction.
            # This is so we don't have buttons needlessly enabled for tweaks with only 1 page
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
    
    # Declare first button
    @ui.button(emoji='⏮️', style=ButtonStyle.blurple, row=1, disabled=True)
    async def first(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            # Set current array page
            self.array_current_page = 0
            # Pull down actual current page
            self.current_page = 1
            # Prepare our embed
            embed = await self.page_formatter(entry=self.pages[self.array_current_page], all_pages=self.pages, current_page=self.current_page)
            # Launch!
            await self.launch(embed)
    
    # Declare previous button
    @ui.button(emoji='⬅️', style=ButtonStyle.blurple, row=1, disabled=True)
    async def previous(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            # Pull down array current page
            self.array_current_page = (self.array_current_page - 1)
            # Pull down actual current page
            self.current_page = (self.current_page - 1)
            # Prepare our embed
            embed = await self.page_formatter(entry=self.pages[self.array_current_page], all_pages=self.pages, current_page=self.current_page)
            # Launch!
            await self.launch(embed)
            
    # Declare stop button
    @ui.button(emoji='⏹️', style=ButtonStyle.blurple, row=1)
    async def pause(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            # Run our timeout function early
            await self.on_timeout()
            
    # Declare next button
    @ui.button(emoji='➡️', style=ButtonStyle.blurple, row=1, disabled=True)
    async def next(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            # Bump up array current page
            self.array_current_page = (self.array_current_page + 1)
            # Bump up actual current page
            self.current_page = (self.current_page + 1)
            # Prepare our embed
            embed = await self.page_formatter(entry=self.pages[self.array_current_page], all_pages=self.pages, current_page=self.current_page)
            # Launch!
            await self.launch(embed)
            
    # Declare last button
    @ui.button(emoji='⏭️', style=ButtonStyle.blurple, row=1, disabled=True)
    async def last(self, button: ui.Button, interaction: Interaction):
        if interaction.user == self.ctx.author:
            # Set current array page
            self.array_current_page = (len(self.pages) - 1)
            # Pull down actual current page
            self.current_page = (self.array_current_page + 1)
            # Prepare our embed
            embed = await self.page_formatter(entry=self.pages[self.array_current_page], all_pages=self.pages, current_page=self.current_page)
            # Launch!
            await self.launch(embed)

    # Timeout function
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