import discord
from discord.ext import commands
from data.services.user_service import user_service
from utils.config import cfg


class StickyRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != cfg.guild_id:
            return

        roles = [role.id for role in member.roles if role < member.guild.me.top_role and role != member.guild.default_role]
        user_service.set_sticky_roles(member.id, roles)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != cfg.guild_id:
            return

        possible_roles = user_service.get_user(member.id).sticky_roles
        roles = [member.guild.get_role(role) for role in possible_roles if member.guild.get_role(role) is not None and member.guild.get_role(role) < member.guild.me.top_role]
        await member.add_roles(*roles, reason="Sticky roles")


def setup(bot):
    bot.add_cog(StickyRoles(bot))
