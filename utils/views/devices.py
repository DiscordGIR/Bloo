import discord
from discord import ui
from utils.context import BlooContext

class Select(ui.Select):
    def __init__(self, versions):
        super().__init__(custom_id="Some identifier", placeholder="Select a version...", min_values=1, max_values=1,
                         options=[discord.SelectOption(label=version) for version in versions])
        self.value = None

    async def callback(self, interaction: discord.Interaction):
        self.value = interaction.data
        self.view.stop()


class FirmwareDropdown(ui.View):
    def __init__(self, firmware_list):
        super().__init__()
        self.ctx = None
        self.pagination_index = 0
        self.max_index = len(
            firmware_list) // 25 if len(firmware_list) % 25 == 0 else (len(firmware_list) // 25) + 1
        self.firmware_list = firmware_list
        self.current_dropdown = Select(firmware_list[:25])

    async def start(self, ctx: BlooContext):
        self.ctx = ctx
        self.add_item(self.current_dropdown)
        await ctx.respond_or_edit(content="Choose a firmware for your device", view=self, ephemeral=True)
        await self.wait()

        return self.current_dropdown.value.get('values')[0] if self.current_dropdown.value.get('values') else None

    @ui.button(label='Older firmwares', style=discord.ButtonStyle.secondary, row=1)
    async def older(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.user == self.ctx.author and self.pagination_index + 1 <= self.max_index:
            self.pagination_index += 1
            await self.refresh_current_dropdown(interaction)

    @ui.button(label='Newer firmwares', style=discord.ButtonStyle.secondary, disabled=True, row=1)
    async def newer(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.user == self.ctx.author and self.pagination_index > 0:
            self.pagination_index -= 1
            await self.refresh_current_dropdown(interaction)

    async def refresh_current_dropdown(self, interaction):
        self.remove_item(self.current_dropdown)
        self.current_dropdown = Select(
            self.firmware_list[self.pagination_index*25:(self.pagination_index+1)*25])

        for child in self.children:
            if child.label == "Older firmwares":
                child.disabled = self.pagination_index + 1 == self.max_index
            elif child.label == "Newer firmwares":
                child.disabled = self.pagination_index == 0

        self.add_item(self.current_dropdown)
        await interaction.response.edit_message(content="Choose a firmware for your device", view=self)


class Confirm(ui.View):
    def __init__(self, ctx: BlooContext, true_response, false_response):
        super().__init__()
        self.ctx = ctx
        self.value = None
        self.true_response = true_response
        self.false_response = false_response

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @ui.button(label='Yes', style=discord.ButtonStyle.success)
    async def confirm(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.user == self.ctx.author:
            self.value = True
            self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @ui.button(label='No', style=discord.ButtonStyle.grey)
    async def cancel(self, button: ui.Button, interaction: discord.Interaction):
        if interaction.user == self.ctx.author:
            await self.ctx.send_warning(description=self.false_response)
            self.value = False
            self.stop()
