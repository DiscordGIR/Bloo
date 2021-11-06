from datetime import datetime
from io import BytesIO
from typing import List

import discord
from data.services import guild_service, user_service
from discord.ext import commands
from discord.utils import format_dt
from utils import cfg


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Log member join messages, send log to #server-logs

        Parameters
        ----------
        member : discord.Member
            The member that joined
        """

        if member.guild.id != cfg.guild_id:
            return

        db_user = user_service.get_user(member.id)
        db_guild = guild_service.get_guild()
        channel = member.guild.get_channel(db_guild.channel_private)

        embed = discord.Embed(title="Member joined")
        embed.color = discord.Color.green()
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(
            name="User", value=f'{member} ({member.mention})', inline=True)
        embed.add_field(name="Warnpoints",
                        value=db_user.warn_points, inline=True)
        embed.add_field(
            name="Join date", value=f"{format_dt(member.joined_at, style='F')} ({format_dt(member.joined_at, style='R')})", inline=True)
        embed.add_field(name="Created",
                        value=f"{format_dt(member.created_at, style='F')} ({format_dt(member.created_at, style='R')})", inline=True)
        embed.timestamp = datetime.now()
        embed.set_footer(text=member.id)

        await channel.send(embed=embed)

        if db_user.is_muted:
            mute_role = db_guild.role_mute
            mute_role = member.guild.get_role(mute_role)
            await member.add_roles(mute_role)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Log member leaves in #server-logs

        Parameters
        ----------
        member : discord.Member
            Member that left
        """

        if member.guild.id != cfg.guild_id:
            return

        db_guild = guild_service.get_guild()
        channel = member.guild.get_channel(db_guild.channel_private)

        embed = discord.Embed(title="Member left")
        embed.color = discord.Color.purple()
        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(
            name="User", value=f'{member} ({member.mention})', inline=True)
        embed.timestamp = datetime.now()
        embed.set_footer(text=member.id)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """Log message edits with before and after content

        Parameters
        ----------
        before : discord.Message
            Before edit message data
        after : discord.Message
            Aftere edit message data
        """

        if not before.guild:
            return
        if before.guild.id != cfg.guild_id:
            return
        if not before.content or not after.content or before.content == after.content:
            return

        db_guild = guild_service.get_guild()
        channel = before.guild.get_channel(db_guild.channel_private)

        embed = discord.Embed(title="Message Updated")
        embed.color = discord.Color.orange()
        embed.set_thumbnail(url=before.author.display_avatar)
        embed.add_field(
            name="User", value=f'{before.author} ({before.author.mention})', inline=False)

        before_content = before.content
        if len(before.content) > 400:
            before_content = before_content[0:400] + "..."

        after_content = after.content
        if len(after.content) > 400:
            after_content = after_content[0:400] + "..."

        embed.add_field(name="Old message", value=before_content, inline=False)
        embed.add_field(name="New message", value=after_content, inline=False)
        embed.add_field(
            name="Channel", value=before.channel.mention + f"\n\n[Link to message]({before.jump_url})", inline=False)
        embed.timestamp = datetime.now()
        embed.set_footer(text=before.author.id)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """Log message deletes

        Parameters
        ----------
        message : discord.Message
            Message that was deleted
        """

        message = payload.cached_message

        if not message or not message.guild:
            return
        if message.guild.id != cfg.guild_id:
            return
        if message.author.bot:
            return
        if message.content == "" or not message.content:
            return

        db_guild = guild_service.get_guild()
        channel = message.guild.get_channel(db_guild.channel_private)

        embed = discord.Embed(title="Message Deleted")
        embed.color = discord.Color.red()
        embed.set_thumbnail(url=message.author.display_avatar)
        embed.add_field(
            name="User", value=f'{message.author} ({message.author.mention})', inline=True)
        embed.add_field(
            name="Channel", value=message.channel.mention, inline=True)
        content = message.content
        if len(message.content) > 400:
            content = content[0:400] + "..."
        embed.add_field(name="Message", value=content +
                        f"\n\n[Link to message]({message.jump_url})", inline=False)
        embed.set_footer(text=message.author.id)
        embed.timestamp = datetime.now()
        await channel.send(embed=embed)

    # @commands.Cog.listener()
    # async def on_command_error(self, ctx: BlooContext, error):
    #     if isinstance(error, commands.CommandNotFound):
    #         return

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: List[discord.Message]):
        """Log bulk message deletes. Messages are outputted to file and sent to #server-logs

        Parameters
        ----------
        messages : [discord.Message]
            List of messages that were deleted
        """

        if not messages[0].guild:
            return
        if messages[0].guild.id != cfg.guild_id:
            return

        members = set()
        db_guild = guild_service.get_guild()
        channel = messages[0].guild.get_channel(db_guild.channel_private)
        output = BytesIO()
        for message in messages:
            members.add(message.author)

            string = f'{message.author} ({message.author.id}) [{message.created_at.strftime("%B %d, %Y, %I:%M %p")}]) UTC\n'
            string += message.content
            for attachment in message.attachments:
                string += f'\n{attachment.url}'

            string += "\n\n"
            output.write(string.encode('UTF-8'))
        output.seek(0)

        member_string = ""
        for i, member in enumerate(members):
            if i == len(members) - 1 and i == 0:
                member_string += f"{member.mention}"
            elif i == len(members) - 1 and i != 0:
                member_string += f"and {member.mention}"
            else:
                member_string += f"{member.mention}, "

        embed = discord.Embed(title="Bulk Message Deleted")
        embed.color = discord.Color.red()
        embed.add_field(
            name="Users", value=f'This batch included {len(messages)} messages from {member_string}', inline=True)
        embed.add_field(
            name="Channel", value=message.channel.mention, inline=True)
        embed.timestamp = datetime.now()
        await channel.send(embed=embed)
        await channel.send(file=discord.File(output, 'message.txt'))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Message, after: discord.Message):
        if not after.guild.id == cfg.guild_id:
            return
        if not before or not after:
            return
        if before.display_name != after.display_name:
            await self.member_nick_update(before, after)
            return

        new_roles = [role.mention
                     for role in after.roles if role not in before.roles]
        if new_roles:
            await self.member_roles_update(member=after, roles=new_roles, added=True)
            return

        removed_roles = [role.mention
                         for role in before.roles if role not in after.roles]
        if removed_roles:
            await self.member_roles_update(member=after, roles=removed_roles, added=False)
            return

    async def member_nick_update(self, before, after):
        embed = discord.Embed(title="Member Renamed")
        embed.color = discord.Color.orange()
        embed.set_thumbnail(url=after.display_avatar)
        embed.add_field(
            name="Member", value=f'{after} ({after.mention})', inline=False)
        embed.add_field(
            name="Old nickname", value=f'{before.display_name}', inline=True)
        embed.add_field(
            name="New nickname", value=f'{after.display_name}', inline=True)
        embed.timestamp = datetime.now()
        embed.set_footer(text=after.id)

        db_guild = guild_service.get_guild()
        private = after.guild.get_channel(db_guild.channel_private)
        if private:
            await private.send(embed=embed)

    async def member_roles_update(self, member, roles, added):
        embed = discord.Embed()
        if added:
            embed.title = "Member Role Added"
            embed.color = discord.Color.blue()
        else:
            embed.title = "Member Role Removed"
            embed.color = discord.Color.red()

        embed.set_thumbnail(url=member.display_avatar)
        embed.add_field(
            name="Member", value=f'{member} ({member.mention})', inline=False)
        embed.add_field(
            name="Role difference", value=', '.join(roles), inline=False)
        embed.timestamp = datetime.now()
        embed.set_footer(text=member.id)

        db_guild = guild_service.get_guild()
        private = member.guild.get_channel(db_guild.channel_private)
        if private:
            await private.send(embed=embed)


def setup(bot):
    bot.add_cog(Logging(bot))
