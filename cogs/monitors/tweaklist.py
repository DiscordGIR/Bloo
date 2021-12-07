import os
import traceback

import aiohttp
import discord
from discord.ext import commands
from utils.logger import logger


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
                        raise Exception(f"Failed to upload paste: {response.status}")
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


def setup(bot):
    if os.environ.get("PASTEE_TOKEN") is None:
        logger.warn(
            "Pastee token not set, not loading the TweakList cog! If you want this, set PASTEE_TOKEN in the .env file.")
        return

    bot.add_cog(Tweaks(bot))
