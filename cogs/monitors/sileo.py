import discord
import re
import aiohttp
import json
from discord.ext import commands
from yarl import URL
from data.services.guild_service import guild_service
from utils.permissions.permissions import permissions


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
                    view.add_item(discord.ui.Button(label='View Depiction', url=response.get(
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
    bot.add_cog(Sileo(bot))
