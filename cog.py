import discord
from discord.commands import Option, context, slash_command
from discord.ext import commands

from utils import cfg


class Example(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(guild_ids=[cfg.guild_id])
    async def ping(self, ctx: context.ApplicationContext):
        await ctx.respond("Pong!", ephemeral=True)

    @slash_command(guild_ids=[cfg.guild_id])
    async def pong(self, ctx: context.ApplicationContext, member: Option(discord.Member, "Choose a member", required=True)):
        await ctx.respond(member.mention)


def setup(bot):
    bot.add_cog(Example(bot))
