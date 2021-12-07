import discord, aiohttp, json, os
from discord.ext import commands
from yarl import URL


class Tweaks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            pass
        else:
            if "apt" in message.content.lower() and "base structure" in message.content.lower() and ("libhooker" or "substitute" or "substrate" in message.content.lower()) and len(message.content.splitlines()) >= 50:
                async with aiohttp.ClientSession(headers={'content-type': 'application/json', 'X-Auth-Token': os.environ.get("PASTEE_TOKEN")}) as session:
                    async with session.post(url='https://api.paste.ee/v1/pastes', json={"description": f"Uploaded by {message.author}","sections":[{"name":f"Uploaded by {message.author}","syntax":"text","contents":message.content}]}) as response:
                        resp = await response.read()
                        pastelink = json.loads(resp).get("link")
                        embed = discord.Embed(title=f"Tweak list", color=discord.Color.green())
                        embed.description = f"You have pasted a tweak list, to reduce chat spam it can be viewed [here]({pastelink})."
                        # Check if the upload was a success
                        if pastelink is not None:
                            await message.delete()
                            await message.channel.send(f'{message.author.mention}', embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
                        else: pass


def setup(bot):
    bot.add_cog(Tweaks(bot))