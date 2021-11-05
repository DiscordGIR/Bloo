import base64
import datetime
import json
import os
import traceback
import typing
from io import BytesIO

import discord
import humanize
import pytimeparse
from data.services.guild_service import guild_service
from discord.commands import slash_command
from discord.commands.errors import ApplicationCommandInvokeError
from discord.ext import commands
from PIL import Image
from utils.config import cfg
from utils.context import BlooContext, PromptData
from utils.permissions.checks import PermissionsFailure, whisper
from utils.permissions.slash_perms import slash_perms


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(3, 15.0, commands.BucketType.channel)

        # self.CIJ_KEY = os.environ.get('CIJ_KEY')
        # self.cij_baseurl = "https://canijailbreak2.com/v1/pls"
        # self.devices_url = "https://api.ipsw.me/v4/devices"

        try:
            with open('emojis.json') as f:
                self.emojis = json.loads(f.read())
        except:
            raise Exception("Could not find emojis.json. Make sure to run grab_emojis.py")
        
    
    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Send yourself a reminder after a given time gap")
    async def remindme(self, ctx: BlooContext, dur: str, *, reminder: str):
        """Send yourself a reminder after a given time gap
        Example usage
        -------------
        /remindme 1h bake the cake
        Parameters
        ----------
        dur : str
            "After when to send the reminder"
        reminder : str
            "What to remind you of"
        """
        now = datetime.datetime.now()
        delta = pytimeparse.parse(dur)
        if delta is None:
            raise commands.BadArgument("Please give me a valid time to remind you! (i.e 1h, 30m)")
        
        time = now + datetime.timedelta(seconds=delta)
        if time < now:
            raise commands.BadArgument("Time has to be in the future >:(")
        reminder = discord.utils.escape_markdown(reminder)

        ctx.tasks.schedule_reminder(ctx.author.id, reminder, time)
        natural_time = humanize.naturaldelta(
            delta, minimum_unit='seconds')
        embed = discord.Embed(title="Reminder set", color = discord.Color.random(), description=f"We'll remind you in {natural_time}")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @slash_command(guild_ids=[cfg.guild_id], description="Post large version of a given emoji")
    async def jumbo(self, ctx: BlooContext, emoji):
        # # non-mod users will be ratelimited
        # bot_chan = guild_service.get_guild().channel_botspam
        # if not self.bot.permissions.hasAtLeast(ctx.guild, ctx.author, 5) and ctx.channel.id != bot_chan:
        #     if await self.ratelimit(ctx.message):
        #         raise commands.BadArgument("This command is on cooldown.")
            
        # is this a regular Unicode emoji?
        print(emoji)
        if self.emojis.get(emoji) is not None:
            # yes, read the bytes from our json file and turn it into an image
            async with ctx.typing():
                emoji_url_file = self.emojis.get(emoji)
                if emoji_url_file is None:
                    raise commands.BadArgument("Couldn't find a suitable emoji.")

            im = Image.open(BytesIO(base64.b64decode(emoji_url_file)))
            image_container = BytesIO()
            im.save(image_container, 'png')
            image_container.seek(0)
            _file = discord.File(image_container, filename="image.png")
            await ctx.respond(file=_file)
        else:
            # no, this is a custom emoji. send its URL
            em = self.bot.get_emoji(int(emoji.split(":",2)[2].replace(">", "")))
            await ctx.respond(em.url)

    async def ratelimit(self, message):
        bucket = self.spam_cooldown.get_bucket(message)
        return bucket.update_rate_limit()




    @remindme.error
    @jumbo.error
    async def info_error(self, ctx: BlooContext, error):
        if (isinstance(error, commands.MissingRequiredArgument)
            or isinstance(error, PermissionsFailure)
            or isinstance(error, commands.BadArgument)
            or isinstance(error, commands.BadUnionArgument)
            or isinstance(error, commands.MissingPermissions)
            or isinstance(error, commands.BotMissingPermissions)
            or isinstance(error, commands.MaxConcurrencyReached)
                or isinstance(error, commands.NoPrivateMessage)):
            await ctx.send_error(error)
        else:
            await ctx.send_error("A fatal error occured. Tell <@109705860275539968> about this.")
            traceback.print_exc()

def setup(bot):
    bot.add_cog(Misc(bot))
