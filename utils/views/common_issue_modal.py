import re
import discord

class CommonIssueModal(discord.ui.Modal):
    def __init__(self, bot, title, author: discord.Member) -> None:
        self.bot = bot
        self.title = title[:20] + "..." if len(title) >= 20 else title
        self.author = author
        self.description = None
        self.buttons = None
        print(len(f"Add common issue — {self.title}"))
        super().__init__(title=f"Add common issue — {self.title}")

        self.add_item(
            discord.ui.InputText(
                label="Body of the common issue",
                placeholder="Enter the body of the common issue",
                style=discord.InputTextStyle.long,
            )
        )
        
        for i in range(2):
            self.add_item(
                discord.ui.InputText(
                    label=f"Button {(i%2)+1} name",
                    placeholder="Enter a name for the button. You can also put an emoji at the start.",
                    style=discord.InputTextStyle.short,
                    required=False,
                    max_length=80
                )
            )
            self.add_item(
                discord.ui.InputText(
                    label=f"Button {(i%2)+1} link",
                    placeholder="Enter a link for the button",
                    style=discord.InputTextStyle.short,
                    required=False
                )
            )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return

        button_names = [child.value.strip() for child in self.children[1::2] if child.value is not None]
        links = [child.value.strip() for child in self.children[2::2] if child.value is not None]

        # make sure all links are valid URLs with regex
        if not all(re.match(r'^(https|http)://.*', link) for link in links):
            await self.send_error(interaction, "The links must be valid URLs!")
            return

        if len(button_names) != len(links):
            await self.send_error(interaction, "All buttons must have labels and links!")
            return

        buttons = list(zip(button_names, links))
        description = self.children[0].value
        if not description:
            await self.send_error(interaction, "Description is missing!")
            return

        for label in button_names:
            custom_emojis = re.search(r'<:\d+>|<:.+?:\d+>|<a:.+:\d+>|[\U00010000-\U0010ffff]', label)
            if custom_emojis is not None:
                emoji = custom_emojis.group(0).strip()
                if not label.startswith(emoji):
                    await self.send_error(interaction, "Emojis must be at the start of labels!")
                    return
                label = label.replace(emoji, '')
                label = label.strip()
                if not label:
                    await self.send_error(interaction, "A button cannot just be an emoji!")
                    return

        self.buttons = buttons
        self.description = description

        self.stop()
        try:
            await interaction.response.send_message()
        except:
            pass

    async def send_error(self, interaction: discord.Interaction, error: str):
        embed = discord.Embed(title=":(\nYour command ran into a problem", description=error, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class EditCommonIssue(discord.ui.Modal):
    def __init__(self, bot, title, issue_message, author: discord.Member) -> None:
        self.bot = bot
        self.author = author
        self.edited = False
        self.title = title[:20] + "..." if len(title) >= 20 else title
        self.description = issue_message.embeds[0].description

        components = issue_message.components
        buttons = []
        if components:
            for component in components:
                if isinstance(component, discord.ActionRow):
                    for child in component.children:
                        buttons.append((f"{str(child.emoji) + ' ' if child.emoji else ''}{child.label}", child.url))

        self.buttons = buttons
        super().__init__(title=f"Edit tag {self.title}")

        self.add_item(
            discord.ui.InputText(
                label="Body of the tag",
                placeholder="Enter the body of the tag",
                style=discord.InputTextStyle.long,
                value=self.description
            )
        )

        for i in range(2):
            self.add_item(
                discord.ui.InputText(
                    label=f"Button {(i%2)+1} name",
                    placeholder="Enter a name for the button. You can also put an emoji at the start.",
                    style=discord.InputTextStyle.short,
                    required=False,
                    max_length=80,
                    value=self.buttons[i][0] if len(self.buttons) > i else None
                )
            )
            self.add_item(
                discord.ui.InputText(
                    label=f"Button {(i%2)+1} link",
                    placeholder="Enter a link for the button",
                    style=discord.InputTextStyle.short,
                    required=False,
                    value=self.buttons[i][1] if len(self.buttons) > i else None
                )
            )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return

        button_names = [child.value.strip() for child in self.children[1::2] if child.value is not None]
        links = [child.value.strip() for child in self.children[2::2] if child.value is not None]

        # make sure all links are valid URLs with regex
        if not all(re.match(r'^(https|http)://.*', link) for link in links):
            await self.send_error(interaction, "The links must be valid URLs!")
            return

        if len(button_names) != len(links):
            await self.send_error(interaction, "All buttons must have labels and links!")
            return

        buttons = list(zip(button_names, links))
        description = self.children[0].value
        if not description:
            await self.send_error(interaction, "Description is missing!")
            return

        for label in button_names:
            custom_emojis = re.search(r'<:\d+>|<:.+?:\d+>|<a:.+:\d+>|[\U00010000-\U0010ffff]', label)
            if custom_emojis is not None:
                emoji = custom_emojis.group(0).strip()
                if not label.startswith(emoji):
                    await self.send_error(interaction, "Emojis must be at the start of labels!")
                    return
                label = label.replace(emoji, '')
                label = label.strip()
                if not label:
                    await self.send_error(interaction, "A button cannot just be an emoji!")
                    return

        self.buttons = buttons
        self.description = description
        self.edited = True

        self.stop()
        try:
            await interaction.response.send_message()
        except:
            pass

    async def send_error(self, interaction: discord.Interaction, error: str):
        embed = discord.Embed(title=":(\nYour command ran into a problem", description=error, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
