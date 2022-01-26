import base64
import datetime
import io
import json
import traceback

import aiohttp
import discord

import pytimeparse
from data.services.guild_service import guild_service
from discord.commands import Option, slash_command
from discord.commands.commands import message_command, user_command
from discord.ext import commands
from PIL import Image
from utils.autocompleters import (bypass_autocomplete, get_ios_cfw,
                                  rule_autocomplete)
from utils.config import cfg
from utils.context import BlooContext
from utils.logger import logger
from utils.menu import BypassMenu
from utils.permissions.checks import (PermissionsFailure, whisper,
                                      whisper_in_general)
from utils.permissions.permissions import permissions
from yarl import URL


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


class BypassDropdown(discord.ui.Select):
    def __init__(self, ctx, apps):
        self.ctx = ctx
        self.apps = {app.get("bundleId"): app for app in apps}
        options = [
            discord.SelectOption(label=app.get("name"), value=app.get("bundleId"), description="Bypasses found" if app.get("bypasses") else "No bypasses found", emoji='<:appstore:392027597648822281>') for app in apps
        ]
        super().__init__(placeholder='Pick an app...',
                         min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        if interaction.user != self.ctx.author:
            return

        self.view.stop()
        app = self.apps.get(self.values[0])
        self.ctx.app = app
        if not app.get("bypasses"):
            await self.ctx.send_error("No bypasses found for this app!")
            return

        menu = BypassMenu(self.ctx, app.get("bypasses"), per_page=1,
                          page_formatter=format_bypass_page, whisper=self.ctx.whisper)
        await menu.start()

    async def on_timeout(self):
        self.disabled = True
        self.placeholder = "Timed out"

        await self.ctx.edit(view=self._view)


def format_bypass_page(ctx, entries, current_page, all_pages):
    ctx.current_bypass = entries[0]
    embed = discord.Embed(title=ctx.app.get(
        "name"), color=discord.Color.blue())
    embed.set_thumbnail(url=ctx.app.get("icon"))

    embed.description = f"You can use **{ctx.current_bypass.get('name')}**!"
    if ctx.current_bypass.get("notes") is not None:
        embed.add_field(name="Note", value=ctx.current_bypass.get('notes'))
        embed.color = discord.Color.orange()
    if ctx.current_bypass.get("version") is not None:
        embed.add_field(name="Supported versions",
                        value=f"This bypass works on versions {ctx.current_bypass.get('version')} of the app")

    embed.set_footer(
        text=f"Powered by ios.cfw.guide • Bypass {current_page} of {len(all_pages)}")
    return embed


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(
            3, 15.0, commands.BucketType.channel)

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
    @slash_command(guild_ids=[cfg.guild_id], description="View information about a CVE")
    async def cve(self, ctx: BlooContext, id: str):
        """View information about a CVE

        Example usage
        -------------
        /cve <id>

        Parameters
        ----------
        id : str
            "ID of CVE to lookup"

        """
        try:
            async with aiohttp.ClientSession() as client:
                async with client.get(URL(f'https://cve.circl.lu/api/cve/{id}', encoded=True)) as resp:
                    response = json.loads(await resp.text())
                    embed = discord.Embed(title=response.get(
                        'id'), color=discord.Color.random())
                    embed.description = response.get('summary')
                    embed.add_field(name="Published", value=response.get(
                        'Published'), inline=True)
                    embed.add_field(name="Last Modified",
                                    value=response.get('Modified'), inline=True)
                    embed.add_field(name="Complexity", value=response.get(
                        'access').get('complexity').title(), inline=False)
                    embed.set_footer(text="Powered by https://cve.circl.lu")
                    await ctx.respond(embed=embed, ephemeral=ctx.whisper)
        except Exception:
            raise commands.BadArgument("Could not find CVE.")

    @whisper_in_general()
    @slash_command(guild_ids=[cfg.guild_id], description="This command is temporarily disabled.")
    async def bypass(self, ctx: BlooContext, app: Option(str, description="Name of the app", autocomplete=bypass_autocomplete)):
        await ctx.defer(ephemeral=ctx.whisper)
        data = await get_ios_cfw()
        bypasses = data.get('bypass')
        matching_apps = [body for a, body in bypasses.items()
                         if app.lower() in a.lower()]

        if not matching_apps:
            raise commands.BadArgument(
                "The API does not recognize that app or there are no bypasses available.")

        # matching_app = bypasses[matching_apps[0]]
        # print(matching_app)
        if len(matching_apps) > 1:
            view = discord.ui.View(timeout=30)
            apps = matching_apps[:25]
            apps.sort(key=lambda x: x.get("name"))
            menu = BypassDropdown(ctx, apps)
            view.add_item(menu)
            view.on_timeout = menu.on_timeout
            embed = discord.Embed(
                description="Which app would you like to view bypasses for?", color=discord.Color.blurple())
            await ctx.respond(embed=embed, view=view, ephemeral=ctx.whisper)
        else:
            ctx.app = matching_apps[0]
            bypasses = ctx.app.get("bypasses")
            if not bypasses or bypasses is None or bypasses == [None]:
                raise commands.BadArgument(
                    f"{ctx.app.get('name')} has no bypasses.")

            menu = BypassMenu(ctx, ctx.app.get(
                "bypasses"), per_page=1, page_formatter=format_bypass_page, whisper=ctx.whisper)
            await menu.start()

    @slash_command(guild_ids=[cfg.guild_id], description="Post the embed for one of the rules")
    async def rule(self, ctx: BlooContext, title: Option(str, autocomplete=rule_autocomplete), user_to_mention: Option(discord.Member, description="User to mention in the response", required=False)):
        if title not in self.bot.rule_cache.cache:
            potential_rules = [r for r in self.bot.rule_cache.cache if title.lower() == r.lower(
            ) or title.strip() == f"{r} - {self.bot.rule_cache.cache[r].description}"[:100].strip()]
            if not potential_rules:
                raise commands.BadArgument(
                    "Rule not found! Title must match one of the embeds exactly, use autocomplete to help!")
            title = potential_rules[0]

        embed = self.bot.rule_cache.cache[title]

        if user_to_mention is not None:
            title = f"Hey {user_to_mention.mention}, have a look at this!"
        else:
            title = None

        await ctx.respond_or_edit(content=title, embed=embed)

    @slash_command(guild_ids=[cfg.guild_id], description="Get the topic for a channel")
    async def topic(self, ctx: BlooContext, channel: Option(discord.TextChannel, description="Channel to get the topic from", required=False), user_to_mention: Option(discord.Member, description="User to mention in the response", required=False)):
        """get the channel's topic"""
        channel = channel or ctx.channel
        if channel.topic is None:
            raise commands.BadArgument(f"{channel.mention} has no topic!")

        if user_to_mention is not None:
            title = f"Hey {user_to_mention.mention}, have a look at this!"
        else:
            title = None

        embed = discord.Embed(title=f"#{channel.name}'s topic",
                              description=channel.topic, color=discord.Color.blue())
        await ctx.respond_or_edit(content=title, embed=embed)

    @topic.error
    @rule.error
    @bypass.error
    @cve.error
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
            logger.error(traceback.format_exc())


def setup(bot):
    bot.add_cog(Misc(bot))
