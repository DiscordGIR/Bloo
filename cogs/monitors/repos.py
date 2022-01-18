import discord
import re
from discord.ext import commands
from data.services.guild_service import guild_service
from utils.autocompleters import fetch_repos
from utils.views.canister import default_repos
from utils.permissions.permissions import permissions


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


def setup(bot):
    bot.add_cog(RepoWatcher(bot))
