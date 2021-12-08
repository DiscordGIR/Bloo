import discord
from discord.ext import commands

import re
from datetime import timezone
from data.services.guild_service import guild_service
from utils.config import cfg
from utils.mod.filter import find_triggered_filters
from utils.mod.global_modactions import mute
from utils.mod.report import report
from utils.permissions.permissions import permissions

class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_filter = r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)\/{1,}[a-zA-Z0-9]+/?'
        self.spoiler_filter = r'\|\|(.*?)\|\|'
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(
            2, 10.0, commands.BucketType.member)

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.run_filter(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _, message):
        await self.run_filter(message)

    @commands.Cog.listener()
    async def on_member_update(self, _, member: discord.Member):
        await self.nick_filter(member)

    async def run_filter(self, message: discord.Message):
        if not message.guild:
            return
        if message.guild.id != cfg.guild_id:
            return
        if message.author.bot:
            return
        if permissions.has(message.guild, message.author, 6):
            return
        db_guild = guild_service.get_guild()
        role_submod = message.guild.get_role(db_guild.role_sub_mod)
        if role_submod is not None and role_submod in message.author.roles:
            return

        # run through filters
        if message.content and await self.bad_word_filter(message, db_guild):
            return

        if permissions.has(message.guild, message.author, 5):
            return
        if message.content and await self.do_invite_filter(message, db_guild):
            return
        if await self.do_spoiler_newline_filter(message, db_guild):
            return

    async def nick_filter(self, member):
        triggered_words = find_triggered_filters(
            member.display_name, member)
        
        if not triggered_words:
            return
        
        await member.edit(nick="change name pls")
        embed = discord.Embed(title="Nickname changed", color=discord.Color.orange())
        embed.description = f"Your nickname contained the word **{triggered_words[0].word}** which is a filtered word. Please change your nickname or ask a Moderator to do it for you."
        try:
            await member.send(embed=embed)
        except Exception:
            pass

    async def bad_word_filter(self, message, db_guild) -> bool:
        triggered_words = find_triggered_filters(
            message.content, message.author)
        if not triggered_words:
            return

        dev_role = message.guild.get_role(db_guild.role_dev)
        
        triggered = False
        for word in triggered_words:
            if word.piracy:
                # ignore if it's a dev saying piracy in #development
                if message.channel.id == db_guild.channel_development and dev_role in message.author.roles:
                    continue

            if word.notify:
                await self.delete(message)
                await self.ratelimit(message)
                await self.do_filter_notify(message, word.word)
                await report(self.bot, message, word.word)
                return

            triggered = True

        if triggered:
            await self.delete(message)
            await self.ratelimit(message)
            await self.do_filter_notify(message, word.word)

        return triggered

    async def do_invite_filter(self, message, db_guild):
        invites = re.findall(self.invite_filter, message.content, flags=re.S)
        if not invites:
            return

        whitelist = db_guild.filter_excluded_guilds
        for invite in invites:
            try:
                invite = await self.bot.fetch_invite(invite)

                id = None
                if isinstance(invite, discord.Invite):
                    if invite.guild is not None:
                        id = invite.guild.id
                    else:
                        id = 123
                elif isinstance(invite, discord.PartialInviteGuild) or isinstance(invite, discord.PartialInviteChannel):
                    id = invite.id

                if id not in whitelist:
                    await self.delete(message)
                    await self.ratelimit(message)
                    await report(self.bot, message, invite, invite=invite)
                    return True

            except discord.NotFound:
                await self.delete(message)
                await self.ratelimit(message)
                await report(self.bot, message, invite, invite=invite)
                return True

        return False

    async def do_spoiler_newline_filter(self, message: discord.Message, db_guild):
        """
        SPOILER FILTER
        """
        if re.search(self.spoiler_filter, message.content, flags=re.S):
            # ignore if dev in dev channel
            dev_role = message.guild.get_role(db_guild.role_dev)
            if message.channel.id == db_guild.channel_development and dev_role in message.author.roles:
                return False

            await self.delete(message)
            return True

        for a in message.attachments:
            if a.is_spoiler():
                await self.delete(message)
                return True
        
        """
        NEWLINE FILTER
        """
        if len(message.content.splitlines()) > 100:
            dev_role = message.guild.get_role(db_guild.role_dev)
            if not dev_role or dev_role not in message.author.roles:
                await self.delete(message)
                await self.ratelimit(message)
                return True

        return False

    async def ratelimit(self, message):
        current = message.created_at.replace(tzinfo=timezone.utc).timestamp()
        bucket = self.spam_cooldown.get_bucket(message)
        if bucket.update_rate_limit(current):
            try:
                ctx = await self.bot.get_context(message)
                ctx.author = ctx.guild.me
                await mute(ctx, message.author, dur_seconds=15*60, reason="Filter spam")
            except Exception:
                return

    async def do_filter_notify(self, message: discord.Message, word):
        member = message.author
        channel = message.channel
        message_to_user = f"Your message contained a word you aren't allowed to say in {member.guild.name}. This could be either hate speech or the name of a piracy tool/source. Please refrain from saying it!"
        footer = "Repeatedly triggering the filter will automatically result in a mute."
        try:
            embed = discord.Embed(
                description=f"{message_to_user}\n\nFiltered word found: **{word}**", color=discord.Color.orange())
            embed.set_footer(text=footer)
            await member.send(embed=embed)
        except Exception:
            embed = discord.Embed(description=message_to_user,
                                  color=discord.Color.orange())
            embed.set_footer(text=footer)
            await channel.send(member.mention, embed=embed, delete_after=10)

        log_embed = discord.Embed(title="Filter Triggered")
        log_embed.color = discord.Color.red()
        log_embed.add_field(name="Member", value=f"{member} ({member.mention})")
        log_embed.add_field(name="Word", value=word)
        log_embed.add_field(name="Message", value=message.content, inline=False)

        log_channel = message.guild.get_channel(guild_service.get_guild().channel_private)
        if log_channel is not None:
            await log_channel.send(embed=log_embed)

    async def delete(self, message):
        try:
            await message.delete()
        except Exception:
            pass


def setup(bot):
    bot.add_cog(Filter(bot))
