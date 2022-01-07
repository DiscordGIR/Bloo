import re
import traceback
from datetime import timezone

import discord
from data.services.guild_service import guild_service
from discord.commands.commands import message_command, user_command
from discord.ext import commands
from utils.config import cfg
from utils.context import BlooContext
from utils.logger import logger
from utils.misc import scam_cache
from utils.mod.filter import find_triggered_filters
from utils.mod.global_modactions import mute
from utils.mod.report import manual_report, report
from utils.permissions.checks import (PermissionsFailure, always_whisper,
                                      mod_and_up)
from utils.permissions.permissions import permissions


class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_filter = r'(?:https?://)?discord(?:(?:app)?\.com/invite|\.gg)\/{1,}[a-zA-Z0-9]+/?'
        self.spoiler_filter = r'\|\|(.*?)\|\|'
        self.spam_cooldown = commands.CooldownMapping.from_cooldown(
            2, 10.0, commands.BucketType.member)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, reacter: discord.Member):
        """Generate a report when a moderator reacts the stop sign emoji on a message

        Parameters
        ----------
        reaction : discord.Reaction
            [description]
        reacter : discord.Member
            [description]
        """
        if reaction.message.guild is None:
            return
        if reaction.message.guild.id != cfg.guild_id:
            return
        if reaction.message.author.bot:
            return
        if reaction.emoji != '🛑':
            return
        if not permissions.has(reacter.guild, reacter, 5):
            return
        if reacter.top_role <= reaction.message.author.top_role:
            return

        await reaction.message.remove_reaction(reaction.emoji, reacter)
        await manual_report(self.bot, reacter, reaction.message)

    @mod_and_up()
    @always_whisper()
    @user_command(guild_ids=[cfg.guild_id], name="Generate report")
    async def generate_report_rc(self, ctx: BlooContext, member: discord.Member) -> None:
        if ctx.author.top_role <= member.top_role:
            raise commands.BadArgument("Target user must have a lower role than yourself.")
        await manual_report(self.bot, ctx.author, member)
        await ctx.send_success("Generated report!")

    @mod_and_up()
    @always_whisper()
    @message_command(guild_ids=[cfg.guild_id], name="Generate report")
    async def generate_report_msg(self, ctx: BlooContext, message: discord.Message) -> None:
        if ctx.author.top_role <= message.author.top_role:
            raise commands.BadArgument("Target user must have a lower role than yourself.")
        await manual_report(self.bot, ctx.author, message)
        await ctx.send_success("Generated report!")

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

        if message.content and await self.scam_filter(message):
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
        embed = discord.Embed(title="Nickname changed",
                              color=discord.Color.orange())
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

    async def scam_filter(self, message: discord.Message):
        for url in scam_cache.scam_jb_urls:
            if url in message.content.lower():
                embed = discord.Embed(title="Fake or scam jailbreak", color=discord.Color.red())
                embed.description = f"Your message contained the link to a **fake jailbreak** ({url}).\n\nIf you installed this jailbreak, remove it from your device immediately and try to get a refund if you paid for it. Jailbreaks *never* cost money and are always free."
                await message.reply(embed=embed)
                return True

        for url in scam_cache.scam_unlock_urls:
            if url in message.content.lower():
                embed = discord.Embed(title="Fake or scam unlock", color=discord.Color.red())
                embed.description = f"Your message contained the link to a **fake unlock** ({url}).\n\nIf you bought a phone second-hand and it arrived iCloud locked, contact the seller to remove it [using these instructions](https://support.apple.com/en-us/HT201351), or get a refund. If it's your own or a passed relative's device and you can prove it, contact Apple Support to remove the lock."
                await message.reply(embed=embed)
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
        log_embed.add_field(
            name="Member", value=f"{member} ({member.mention})")
        log_embed.add_field(name="Word", value=word)
        log_embed.add_field(
            name="Message", value=message.content, inline=False)

        log_channel = message.guild.get_channel(
            guild_service.get_guild().channel_private)
        if log_channel is not None:
            await log_channel.send(embed=log_embed)

    async def delete(self, message):
        try:
            await message.delete()
        except Exception:
            pass

    @generate_report_msg.error
    @generate_report_rc.error
    async def info_error(self,  ctx: BlooContext, error):
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
    bot.add_cog(Filter(bot))
