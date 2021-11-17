import discord
from discord.commands import Option, slash_command
from discord.commands.commands import message_command, user_command
from discord.ext import commands

import base64
import datetime
import io
import json
import traceback
import aiohttp
import humanize
import pytimeparse
from PIL import Image
from data.services.guild_service import guild_service
from utils.async_cache import async_cacher
from utils.autocompleters import jb_autocomplete
from utils.config import cfg
from utils.context import BlooContext
from utils.database import Guild
from utils.permissions.checks import PermissionsFailure, whisper, whisper_in_general
from utils.permissions.permissions import permissions


@async_cacher()
async def get_jailbreaks_jba():
    """Gets all apps on Jailbreaks.app
    
    Returns
    -------
    dict
        "Apps"
    """
    res_apps = []
    async with aiohttp.ClientSession() as session:
        async with session.get("https://jailbreaks.app/json/apps.json") as resp:
            if resp.status == 200:
                data = await resp.text()
                res_apps = json.loads(data)
    return res_apps


@async_cacher()
async def get_jailbreaks():
    """Gets all jailbreaks on stkc's API
    
    Returns
    -------
    list
        "Jailbreaks"
    """
    response = {}
    async with aiohttp.ClientSession() as client:
        async with client.get('https://assets.stkc.win/jailbreaks.json') as resp:
            if resp.status == 200:
                data = await resp.text()
                response = json.loads(data)
    return response


async def iterate_apps(query) -> dict:
    """Iterates through Jailbreaks.app apps, looking for a matching query
    
    Parameters
    ----------
    query : str
        "App to look for"
        
    Returns
    -------
    dict
        "List of apps that match the query"
    
    """
    apps = await get_jailbreaks_jba()
    for possibleApp in apps:
        if possibleApp.get('name').lower() == query.lower().replace("œ", "oe"):
            return possibleApp


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
            avatar = self.member.avatar or self.member.default_avatar
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
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(
            3, 15.0, commands.BucketType.channel)

        # self.CIJ_KEY = os.environ.get('CIJ_KEY')
        # self.cij_baseurl = "https://canijailbreak2.com/v1/pls"
        # self.devices_url = "https://api.ipsw.me/v4/devices"

        try:
            with open('emojis.json') as f:
                self.emojis = json.loads(f.read())
        except:
            raise Exception(
                "Could not find emojis.json. Make sure to run scrape_emojis.py")

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Send yourself a reminder after a given time gap")
    async def remindme(self, ctx: BlooContext, reminder: Option(str, description="What do you want to be reminded?"), duration: Option(str, description="When do we remind you? (i.e 1m, 1h, 1d)")):
        """Sends you a reminder after a given time gap
        
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
        delta = pytimeparse.parse(duration)
        if delta is None:
            raise commands.BadArgument(
                "Please give me a valid time to remind you! (i.e 1h, 30m)")

        time = now + datetime.timedelta(seconds=delta)
        if time < now:
            raise commands.BadArgument("Time has to be in the future >:(")
        reminder = discord.utils.escape_markdown(reminder)

        ctx.tasks.schedule_reminder(ctx.author.id, reminder, time)
        # natural_time = humanize.naturaldelta(
        #     delta, minimum_unit='seconds')
        embed = discord.Embed(title="Reminder set", color=discord.Color.random(
        ), description=f"We'll remind you {discord.utils.format_dt(time, style='R')}")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper, delete_after=5)

    @slash_command(guild_ids=[cfg.guild_id], description="Post large version of a given emoji")
    async def jumbo(self, ctx: BlooContext, emoji: str):
        """Posts large version of a given emoji
        
        Example usage
        -------------
        /jumbo <emote>
        
        Parameters
        ----------
        emoji : str
            "Emoji to enlarge"
        
        """
        # non-mod users will be ratelimited
        bot_chan = guild_service.get_guild().channel_botspam
        if not permissions.has(ctx.guild, ctx.author, 5) and ctx.channel.id != bot_chan:
            bucket = self.spam_cooldown.get_bucket(ctx.interaction)
            if bucket.update_rate_limit():
                raise commands.BadArgument("This command is on cooldown.")

        # is this a regular Unicode emoji?
        try:
            em = await commands.PartialEmojiConverter().convert(ctx, emoji)
        except commands.PartialEmojiConversionFailure:
            em = emoji
        if isinstance(em, str):
            async with ctx.typing():
                emoji_url_file = self.emojis.get(em)
                if emoji_url_file is None:
                    raise commands.BadArgument(
                        "Couldn't find a suitable emoji.")

            im = Image.open(io.BytesIO(base64.b64decode(emoji_url_file)))
            image_conatiner = io.BytesIO()
            im.save(image_conatiner, 'png')
            image_conatiner.seek(0)
            _file = discord.File(image_conatiner, filename='image.png')
            await ctx.respond(file=_file)
        else:
            await ctx.respond(em.url)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Get avatar of another user or yourself.")
    async def avatar(self, ctx: BlooContext, member: Option(discord.Member, description="User to get avatar of", required=False)) -> None:
        """Posts large version of a given emoji
        
        Example usage
        -------------
        /avatar member:<member>
        
        Parameters
        ----------
        member : discord.Member, optional
            "Member to get avatar of"
        
        """
        if member is None:
            member = ctx.author

        await self.handle_avatar(ctx, member)
    
    @whisper()
    @user_command(guild_ids=[cfg.guild_id], name="View avatar")
    async def avatar_rc(self, ctx: BlooContext, member: discord.Member):
        await self.handle_avatar(ctx, member)
    
    @whisper()
    @message_command(guild_ids=[cfg.guild_id], name="View avatar")
    async def avatar_msg(self, ctx: BlooContext, message: discord.Message):
        await self.handle_avatar(ctx, message.author)
    
    async def handle_avatar(self, ctx, member: discord.Member):
        embed = discord.Embed(title=f"{member}'s avatar")
        animated = ["gif", "png", "jpeg", "webp"]
        not_animated = ["png", "jpeg", "webp"]

        avatar = member.avatar or member.default_avatar
        def fmt(format_):
            return f"[{format_}]({avatar.replace(format=format_, size=4096)})"

        if member.display_avatar.is_animated():
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in animated])}"
        else:
            embed.description = f"View As\n {'  '.join([fmt(format_) for format_ in not_animated])}"

        embed.set_image(url=avatar.replace(size=4096))
        embed.color = discord.Color.random()

        view = PFPView(ctx)
        if member.guild_avatar is not None:
            view.add_item(PFPButton(ctx, member))

        view.message = await ctx.respond(embed=embed, ephemeral=ctx.whisper, view=view)

    @whisper_in_general()
    @slash_command(guild_ids=[cfg.guild_id], description="Get info about a jailbreak.")
    async def jailbreak(self, ctx: BlooContext, name: Option(str, description="Name of the jailbreak", autocomplete=jb_autocomplete, required=True), whisper: Option(bool, description="Whisper? (No by default)", required=False)) -> None:
        """Fetches info of jailbreak
        
        Example usage
        -------------
        /jailbreak name:<name>
        
        Parameters
        ----------
        name : str
            "Name of jailbreak"
        whisper : bool, optional
            "Should we whisper?"
        
        """
        response = await get_jailbreaks()
        try:
            for object in response[f'{name.lower().replace("œ", "oe")}']:
                view = None
                embed = discord.Embed(
                    title=object.get('Name'), color=discord.Color.blurple())
                embed.add_field(
                    name="Version", value=object['LatestVersion'], inline=True)
                embed.add_field(name="Compatible with",
                                value=object['Versions'], inline=True)
                embed.add_field(
                    name="Type", value=object['Type'], inline=False)
                embed.add_field(
                    name="Website", value=object['Website'], inline=False)
                if object.get('Guide') is not None:
                    embed.add_field(
                        name="Guide", value=object['Guide'], inline=False)
                if object.get('Notes') is not None:
                    embed.add_field(
                        name="Notes", value=object['Notes'], inline=False)
                jba = await iterate_apps(object.get('Name'))
                if jba is not None:
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label='Install with Jailbreaks.app', url=f"https://api.jailbreaks.app/install/{jba.get('name').replace(' ', '')}", style=discord.ButtonStyle.url))
                if object.get('Icon') is not None:
                    embed.set_thumbnail(url=object.get('Icon'))
                if object.get('Color') is not None:
                    embed.color = int(object.get('Color').replace('#', ''), 16)
                if view is not None:
                    await ctx.respond_or_edit(embed=embed, ephemeral=ctx.whisper, view=view)
                else:
                    await ctx.respond_or_edit(embed=embed, ephemeral=ctx.whisper)
        except:
            await ctx.send_error("Sorry, I couldn't find any jailbreaks with that name.")

    @jailbreak.error
    @remindme.error
    @jumbo.error
    @avatar.error
    async def info_error(self, ctx: BlooContext, error):
        if isinstance(error, discord.ApplicationCommandInvokeError):
            error = error.original

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
