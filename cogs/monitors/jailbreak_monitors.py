import json
import os
import re
import traceback

import aiohttp
import discord
from data.services.guild_service import guild_service
from discord.ext import commands
from utils.autocompleters import fetch_repos
from utils.logger import logger
from utils.permissions.permissions import permissions
from utils.views.canister import default_repos
from yarl import URL


class RepoWatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id == guild_service.get_guild().channel_general and not permissions.has(message.guild, message.author, 5):
            return

        url = re.search(r'(https?://\S+)', message.content)
        if url is None:
            return

        repos = await fetch_repos()
        repos = [repo['uri'].lower() for repo in repos if repo.get('uri')]

        potential_repo = url.group(0).rstrip("/").lower()
        if any(repo in potential_repo for repo in default_repos):
            return

        if potential_repo not in repos:
            return

        view = discord.ui.View()

        view.add_item(discord.ui.Button(label='Add Repo to Sileo', emoji="<:sileo:679466569407004684>",
                                        url=f"https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={potential_repo}", style=discord.ButtonStyle.url))
        view.add_item(discord.ui.Button(label='Add Repo to Zebra', emoji="<:zebra:911433583032422420>",
                                        url=f"https://sharerepo.stkc.win/v2/?pkgman=zebra&repo={potential_repo}", style=discord.ButtonStyle.url))
        view.add_item(discord.ui.Button(label='Other Package Managers', emoji=":cydiasileosplit:932650041099825232",
                                        url=f"https://sharerepo.stkc.win/?repo={potential_repo}", style=discord.ButtonStyle.url))

        await message.reply(file=discord.File("data/images/transparent1x1.png"), view=view, mention_author=False)


class Tweaks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not ("apt" in message.content.lower() and "base structure" in message.content.lower() and ("libhooker" or "substitute" or "substrate" in message.content.lower()) and len(message.content.splitlines()) >= 50):
            return

        async with aiohttp.ClientSession(headers={'content-type': 'application/json', 'X-Auth-Token': os.environ.get("PASTEE_TOKEN")}) as session:
            async with session.post(url='https://api.paste.ee/v1/pastes', json={"description": f"Uploaded by {message.author}", "sections": [{"name": f"Uploaded by {message.author}", "syntax": "text", "contents": message.content}]}) as response:
                if response.status != 201:
                    try:
                        raise Exception(
                            f"Failed to upload paste: {response.status}")
                    except Exception:
                        logger.error(traceback.format_exc())

                resp = await response.json()
                pastelink = resp.get("link")
                if pastelink is None:
                    return

                embed = discord.Embed(
                    title=f"Tweak list", color=discord.Color.green())
                embed.description = f"You have pasted a tweak list, to reduce chat spam it can be viewed [here]({pastelink})."

                await message.delete()
                await message.channel.send(message.author.mention, embed=embed)


class Sileo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id == guild_service.get_guild().channel_general and not permissions.has(message.guild, message.author, 5):
            return

        urlscheme = re.search(
            "sileo:\/\/package\/([a-zA-Z0-9]+(\.[a-zA-Z0-9]+)+(\.[a-zA-Z0-9]+)+)", message.content)
        if urlscheme is None:
            return

        try:
            async with aiohttp.ClientSession() as client:
                async with client.get(URL(f'https://api.parcility.co/db/package/{urlscheme.group(1)}', encoded=True)) as resp:
                    if resp.status == 200:
                        response = json.loads(await resp.text())

                view = discord.ui.View()
                embed = discord.Embed(
                    title=f"{response.get('data')['Name']} - {response.get('data')['repo']['label']}", color=discord.Color.green())
                embed.description = f"You have linked to a package, you can use the above link to open it directly in Sileo."
                embed.set_thumbnail(url=response.get('data')['Icon'])
                view.add_item(discord.ui.Button(label='Add Repo to Sileo', emoji="<:sileo:679466569407004684>",
                              url=f"https://sharerepo.stkc.win/v2/?pkgman=sileo&repo={response.get('data')['repo']['url']}", style=discord.ButtonStyle.url))
                try:
                    view.add_item(discord.ui.Button(label='View Depiction', emoji="🔎", url=response.get(
                        'data')['Depiction'], style=discord.ButtonStyle.url))
                except:
                    view.add_item(discord.ui.Button(
                        label='View on Parcility', url=f"https://parcility.co/package/{urlscheme.group(1)}", style=discord.ButtonStyle.url))
                await message.reply(f'<sileo://package/{urlscheme.group(1)}>', embed=embed, view=view, allowed_mentions=discord.AllowedMentions(users=True))
        except:
            embed = discord.Embed(title=f"Unknown Package",
                                  color=discord.Color.green())
            embed.description = f"You have linked to a package, you can use the above link to open it directly in Sileo."
            await message.reply(f'<sileo://package/{urlscheme.group(1)}>', embed=embed)


def setup(bot):
    if os.environ.get("PASTEE_TOKEN") is None:
        logger.warn(
            "Pastee token not set, not loading the TweakList cog! If you want this, refer to README.md.")
        return

    bot.add_cog(Tweaks(bot))
    bot.add_cog(RepoWatcher(bot))
    bot.add_cog(Sileo(bot))
