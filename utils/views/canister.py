import io
import re
from datetime import datetime
from typing import IO

import aiohttp
import discord
from colorthief import ColorThief
from utils.context import BlooContext, BlooOldContext
from utils.menu import TweakMenu

pattern = re.compile(
    r"((http|https)\:\/\/)[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*")

default_repos = [
    "apt.bingner.com",
    "apt.procurs.us",
    "apt.saurik.com",
    "apt.oldcurs.us",
    "repo.chimera.sh",
    "diatr.us/apt",
    "repo.theodyssey.dev",
]


async def format_tweak_page(ctx, entries, current_page, all_pages):
    """Formats the page for the tweak embed.

    Parameters
    ----------
    entries : List[dict]
        "The list of dictionaries for each tweak"
    all_pages : list
        "All entries that we will eventually iterate through"
    current_page : number
        "The number of the page that we are currently on"

    Returns
    -------
    discord.Embed
        "The embed that we will send"

    """
    entry = entries[0]
    ctx.repo = entry.get('repository').get('uri')
    ctx.depiction = entry.get('depiction')

    for repo in default_repos:
        if repo in entry.get('repository').get('uri'):
            ctx.repo = None
            break

    titleKey = entry.get('name')

    if entry.get('name') is None:
        titleKey = entry.get('identifier')
    embed = discord.Embed(title=titleKey, color=discord.Color.blue())
    embed.description = discord.utils.escape_markdown(
        entry.get('description')) or "No description"

    if entry.get('author') is not None:
        embed.add_field(name="Author", value=discord.utils.escape_markdown(
            entry.get('author').split("<")[0]), inline=True)
    else:
        embed.add_field(name="Author", value=discord.utils.escape_markdown(
            entry.get('maintainer').split("<")[0]), inline=True)

    embed.add_field(name="Version", value=discord.utils.escape_markdown(
        entry.get('latestVersion') or "No Version"), inline=True)
    embed.add_field(name="Price", value=entry.get(
        "price") or "Free", inline=True)
    embed.add_field(
        name="Repo", value=f"[{entry.get('repository').get('name')}]({entry.get('repository').get('uri')})" or "No Repo", inline=True)
    embed.add_field(name="Bundle ID", value=entry.get(
        "identifier") or "Not found", inline=True)
    if entry.get('tintColor') is None and entry.get('packageIcon') is not None and pattern.match(entry.get('packageIcon')):
        async with aiohttp.ClientSession() as session:
            async with session.get(entry.get('packageIcon')) as icon:
                if icon.status == 200:
                    color = ColorThief(IO.BytesIO(await icon.read())).get_color(quality=1000)
                    embed.color = discord.Color.from_rgb(
                        color[0], color[1], color[2])
                else:
                    embed.color = discord.Color.blue()
    elif entry.get('tintColor') is not None:
        embed.color = int(entry.get('tintColor').replace('#', '0x'), 0)

    if entry.get('packageIcon') is not None and pattern.match(entry.get('packageIcon')):
        embed.set_thumbnail(url=entry.get('packageIcon'))
    embed.set_footer(icon_url=f"{'https://assets.stkc.win/bigboss-sileo.png' if 'http://apt.thebigboss.org/repofiles/cydia/CydiaIcon.png' in entry.get('repository').get('uri')+'/CydiaIcon.png' else entry.get('repository').get('uri')+'/CydiaIcon.png'}",
                     text=f"Powered by Canister • Page {current_page}/{len(all_pages)}" or "No Package")
    embed.timestamp = datetime.now()
    return embed


async def canister(ctx: BlooContext, interaction: bool, whisper: bool, result):
    await TweakMenu(ctx, result, per_page=1, page_formatter=format_tweak_page, whisper=whisper, start_page=25, show_skip_buttons=False, non_interaction_message=ctx.message).start()

class TweakDropdown(discord.ui.Select):
    def __init__(self, author, entries, interaction, should_whisper):
        self.author = author
        self.interaction = interaction
        self.raw_entries = entries
        self.should_whisper = should_whisper
        entries = entries[:24]
        self.current_entry = entries[0]
        self.entries = {entry.get("identifier"): entry for entry in entries}
        options = [discord.SelectOption(label=(option.get("name") or option.get('identifier'))[:100] or "No title", description=f"{option.get('author').split('<')[0] if option.get('author') is not None else option.get('maintainer').split('<')[0]} • {option.get('repository').get('name')}"[:100], value=option.get(
            "identifier"), emoji="<:sileo_tweak_icon:922017793677869056>") for option in entries]

        if len(self.raw_entries) > 24:
            options.append(discord.SelectOption(
                label=f"View {len(self.raw_entries) - 24} more results...", value="view_more"))
        super().__init__(placeholder='Pick a tweak to view...',
                         min_values=1, max_values=1, options=options)

    def start(self, ctx):
        self.ctx = ctx

    async def callback(self, interaction):
        if interaction.user != self.author:
            return

        if self.values[0] == "view_more":
            self.ctx.author = self.author
            if self.interaction:
                await canister(self.ctx, self.interaction, self.should_whisper, self.raw_entries)
            else:
                await canister(self.ctx, False, False, self.raw_entries)
            self._view.stop()
            return

        selected_value = self.entries.get(self.values[0])
        if selected_value is None:
            return

        self.refresh_view(selected_value)
        if self.interaction:
            await self.ctx.edit(embed=await self.format_tweak_page(selected_value), view=self._view)
        else:
            await self.ctx.message.edit(embed=await self.format_tweak_page(selected_value), view=self._view)

    async def on_timeout(self):
        self.disabled = True
        self.placeholder = "Timed out"

        if self.interaction:
            await self.ctx.edit(view=self._view)
        else:
            await self.ctx.message.edit(view=self._view)

    async def format_tweak_page(self, entry):
        titleKey = entry.get('name')

        if entry.get('name') is None:
            titleKey = entry.get('identifier')
        embed = discord.Embed(title=titleKey, color=discord.Color.blue())
        embed.description = discord.utils.escape_markdown(
            entry.get('description')) or "No description"

        if entry.get('author') is not None:
            embed.add_field(name="Author", value=discord.utils.escape_markdown(
                entry.get('author').split("<")[0]), inline=True)
        else:
            embed.add_field(name="Author", value=discord.utils.escape_markdown(
                entry.get('maintainer').split("<")[0]), inline=True)

        embed.add_field(name="Version", value=discord.utils.escape_markdown(
            entry.get('latestVersion') or "No Version"), inline=True)
        embed.add_field(name="Price", value=entry.get(
            "price") or "Free", inline=True)
        embed.add_field(
            name="Repo", value=f"[{entry.get('repository').get('name')}]({entry.get('repository').get('uri')})" or "No Repo", inline=True)
        embed.add_field(name="Bundle ID", value=entry.get(
            "identifier") or "Not found", inline=True)
        if entry.get('tintColor') is None and entry.get('packageIcon') is not None and pattern.match(entry.get('packageIcon')):
            async with aiohttp.ClientSession() as session:
                async with session.get(entry.get('packageIcon')) as icon:
                    if icon.status == 200:
                        color = ColorThief(io.BytesIO(await icon.read())).get_color(quality=1000)
                        embed.color = discord.Color.from_rgb(
                            color[0], color[1], color[2])
                    else:
                        embed.color = discord.Color.blue()
        elif entry.get('tintColor') is not None:
            embed.color = int(entry.get('tintColor').replace('#', '0x'), 0)

        if entry.get('packageIcon') is not None and pattern.match(entry.get('packageIcon')):
            embed.set_thumbnail(url=entry.get('packageIcon'))
        embed.set_footer(icon_url=f"{'https://assets.stkc.win/bigboss-sileo.png' if 'http://apt.thebigboss.org/repofiles/cydia/CydiaIcon.png' in entry.get('repository').get('uri')+'/CydiaIcon.png' else entry.get('repository').get('uri')+'/CydiaIcon.png'}",
                         text=f"Powered by Canister" or "No Package")
        embed.timestamp = datetime.now()
        return embed

    def generate_buttons(self, entry):
        repo = entry.get('repository').get('uri')
        depiction = entry.get('depiction')

        for repo in default_repos:
            if repo in entry.get('repository').get('uri'):
                repo = None
                break

        if repo is not None:
            extra_buttons = [
                discord.ui.Button(label='Add Repo to Sileo', emoji="<:sileo:679466569407004684>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={repo}', style=discord.ButtonStyle.url),
                discord.ui.Button(label='Add Repo to Zebra', emoji="<:zebra:911433583032422420>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={repo}', style=discord.ButtonStyle.url)
            ]
        else:
            extra_buttons = [
                discord.ui.Button(label='Cannot add default repo', emoji="<:sileo:679466569407004684>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={repo}', disabled=True, style=discord.ButtonStyle.url),
                discord.ui.Button(label='Cannot add default repo', emoji="<:zebra:911433583032422420>",
                                  url=f'https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={repo}', disabled=True, style=discord.ButtonStyle.url)
            ]
        if depiction is not None:
            extra_buttons.insert(0,
                                 discord.ui.Button(label='View Depiction', emoji="🔎",
                                                   url=depiction, style=discord.ButtonStyle.url),
                                 )
        return extra_buttons

    def refresh_view(self, entry):
        extra_buttons = self.generate_buttons(entry)
        self._view.clear_items()

        if len(self.raw_entries) > 1:
            self._view.add_item(self)

        for button in extra_buttons:
            self._view.add_item(button)
