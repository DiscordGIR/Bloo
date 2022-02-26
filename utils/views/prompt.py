import discord


class GenericDescriptionModal(discord.ui.Modal):
    def __init__(self, author: discord.Member, title: str, label: str = "Description", placeholder: str = "Please enter a description", prefill: str = ""):
        self.author = author
        self.value = None

        super().__init__(title=title)

        self.add_item(
            discord.ui.InputText(
                label=label,
                placeholder=placeholder,
                style=discord.InputTextStyle.long,
                value=prefill
            )
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return

        self.value = self.children[0].value
        try:
            await interaction.response.send_message()
        except:
            pass

        self.stop()
