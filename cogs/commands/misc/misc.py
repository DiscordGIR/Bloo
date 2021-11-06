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
from discord.commands.commands import Option
from discord.ext import commands
from discord.ext.commands.converter import PartialEmojiConverter
from discord.ext.commands.errors import PartialEmojiConversionFailure
from PIL import Image
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.checks import PermissionsFailure, whisper
from utils.permissions.permissions import permissions


class PFPView(discord.ui.View):
    def __init__(self, ctx: BlooContext):
        super().__init__(timeout=30)
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.ctx.respond_or_edit(view=self)

class PFPButton(discord.ui.Button):
    def __init__(self, ctx: BlooContext, member: discord.Member):
        super().__init__(label="Show other avatar", style=discord.ButtonStyle.primary)
        self.ctx = ctx
        self.member = member
        self.other = False

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return 
        if not self.other:
            avatar = self.member.guild_avatar
            self.other = not self.other
        else:
            avatar = self.member.avatar
            self.other = not self.other

        embed = interaction.message.embeds[0]
        embed.set_image(url=avatar.replace(size=4096))

        animated = ["gif", "png", "jpeg", "webp"]
        not_animated = ["png", "jpeg", "webp"]

        def fmt(format_):
            return f"[{format_}]({avatar.replace(format=format_, size=4096)})"

        if avatar.is_animated():
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in animated])}"
        else:
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in not_animated])}"

        await interaction.response.edit_message(embed=embed)


        
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
            raise Exception("Could not find emojis.json. Make sure to run scrape_emojis.py")
        
    
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
    async def jumbo(self, ctx: BlooContext, emoji: str):
        # non-mod users will be ratelimited
        bot_chan = guild_service.get_guild().channel_botspam
        if not permissions.has(ctx.guild, ctx.author, 5) and ctx.channel.id != bot_chan:
            # TODO: add ratelimit
            ...
            
        # is this a regular Unicode emoji?
        try:
            em = await PartialEmojiConverter().convert(ctx, emoji)
        except PartialEmojiConversionFailure:
            em = emoji
        if isinstance(em, str):
            async with ctx.typing():
                emoji_url_file = self.emojis.get(em)
                if emoji_url_file is None:
                    raise commands.BadArgument("Couldn't find a suitable emoji.")

            im = Image.open(BytesIO(base64.b64decode(emoji_url_file)))
            image_conatiner = BytesIO()
            im.save(image_conatiner, 'png')
            image_conatiner.seek(0)
            _file = discord.File(image_conatiner, filename='image.png')
            await ctx.respond(file=_file)
        else:
            await ctx.respond(em.url)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get avatar of another user or yourself.")
    async def avatar(self, ctx: BlooContext, member: Option(discord.Member, description="User to get avatar of", required=False)) -> None:
        if member is None:
            member = ctx.author

        embed = discord.Embed(title=f"{member}'s avatar")
        animated = ["gif", "png", "jpeg", "webp"]
        not_animated = ["png", "jpeg", "webp"]

        def fmt(format_):
            return f"[{format_}]({member.avatar.replace(format=format_, size=4096)})"

        if member.avatar.is_animated():
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in animated])}"
        else:
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in not_animated])}"
        
        embed.set_image(url=member.avatar.replace(size=4096))
        embed.color = discord.Color.random()
        embed.set_footer(text=f"Requested by {ctx.author}")

        view = PFPView(ctx)
        if member.guild_avatar is not None:
            view.add_item(PFPButton(ctx, member))

        view.message = await ctx.respond(embed=embed, ephemeral=ctx.whisper, view=view)

    

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
