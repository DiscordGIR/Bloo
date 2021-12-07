import discord, aiohttp, json
from discord.ext import tasks, commands
from yarl import URL


class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status.start()

    @tasks.loop(seconds=3600)
    async def status(self):
        async with aiohttp.ClientSession() as client:
            async with client.get(URL('https://api.parcility.co/db/repo/procursus', encoded=True)) as resp:
                if resp.status == 200:
                    response = json.loads(await resp.text())
                    pkg = response.get('data')['package_count']
                    sec = response.get('data')['section_count']
                    await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{pkg} packages, {sec} sections'))
                else:
                    await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='Failed to refresh package and section counts'))

    @status.before_loop
    async def before_status(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Status(bot))