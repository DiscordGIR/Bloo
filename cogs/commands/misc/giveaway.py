import datetime
import random
import traceback

import discord
import humanize
import pytimeparse
from data.model.giveaway import Giveaway as GiveawayDB
from data.services.guild_service import guild_service
from discord.commands.commands import slash_command
from discord.commands.errors import ApplicationCommandInvokeError
from discord.ext import commands, tasks
from utils.config import cfg
from utils.context import BlooContext, PromptData
from utils.permissions.checks import PermissionsFailure, admin_and_up
from utils.permissions.slash_perms import slash_perms
from utils.tasks import end_giveaway


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_messages = {}
        self.time_updater_loop.start()
    
    def cog_unload(self) -> None:
        self.time_updater_loop.cancel()
    
    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Start a giveaway.", permissions=slash_perms.admin_and_up())
    async def giveawaystart(self, ctx: BlooContext, sponsor: discord.Member = None, time: str = None, winners: int = -1, channel: discord.TextChannel = None):
        
        await ctx.defer(ephemeral=True)
        prompts = {
            'name': PromptData(
                value_name="name",
                description="Enter a name for the giveaway.",
                convertor=str
            ),
            'sponsor': PromptData(
                value_name="sponsor",
                description="Tag or give the ID of the sponsor of this giveaway.",
                convertor=commands.MemberConverter().convert
            ), 
            'time': PromptData(
                value_name="time",
                description="How long should this giveaway last? (e.g 10m).",
                convertor=pytimeparse.parse
            ), 
            'winners': PromptData(
                value_name="winner_count",
                description="How many winners should this giveaway have?",
                convertor=int
            ), 
            'channel': PromptData(
                value_name="channel",
                description="Mention the channel to post the giveaway in.",
                convertor=commands.TextChannelConverter().convert
            ), 
        }
        
        # store responses for prompts in one place
        responses = {
            'name': None,
            'sponsor': sponsor,
            'time': pytimeparse.parse(time) if time is not None else None,
            'winners': None if winners < 1 else winners,
            'channel': channel
        }

        for response in responses:
            if responses[response] is None:
                res = await ctx.prompt(prompts[response])
                if res is None:
                    await ctx.send("Giveaway cancelled.")
                    return

                if response == 'winners' and res < 1:
                    await ctx.send_warning("Can't have less than 1 winner!")
                    return
                
                responses[response] = res

        # calculate end time
        now = datetime.datetime.now()
        delta = responses['time']
        end_time = now + datetime.timedelta(seconds=delta)

        # prepare giveaway embed and post it in giveaway channel
        embed = discord.Embed(title="New giveaway!")
        embed.description = f"**{responses['name']}** is being given away by {responses['sponsor'].mention} to **{responses['winners']}** lucky {'winner' if responses['winners'] == 1 else 'winers'}!"
        embed.add_field(name="Time remaining", value=f"Less than {humanize.naturaldelta(end_time - now)}")
        embed.timestamp = end_time
        embed.color = discord.Color.random()
        embed.set_footer(text="Ends")

        message = await responses['channel'].send(embed=embed)
        await message.add_reaction('🎉')

        # store giveaway in database
        giveaway = GiveawayDB(
            _id=message.id,
            channel=responses['channel'].id,
            name=responses['name'],
            winners=responses['winners'],
            end_time=end_time,
            sponsor=responses['sponsor'].id)
        giveaway.save()

        await ctx.send_success(f"Giveaway created!")
        
        ctx.tasks.schedule_end_giveaway(channel_id=responses['channel'].id, message_id=message.id, date=end_time, winners=responses['winners'])

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Pick a new winner of an already ended giveaway.", permissions=slash_perms.admin_and_up())
    async def giveawayreroll(self, ctx: BlooContext, message_id: str):
        
        g = guild_service.get_giveaway(_id=int(message_id))

        if g is None:
            raise commands.BadArgument("Couldn't find an ended giveaway by the provided ID.")
        elif not g.is_ended:
            raise commands.BadArgument("That giveaway hasn't ended yet!")
        elif len(g.entries) == 0:
            raise commands.BadArgument(f"There are no entries for the giveaway of **{g.name}**.")
        elif len(g.entries) <= len(g.previous_winners):
            raise commands.BadArgument("No more winners are possible!")

        the_winner = None
        while the_winner is None:
            random_id = random.choice(g.entries)
            the_winner = ctx.guild.get_member(random_id)
            if the_winner is not None and the_winner.id not in g.previous_winners:
                break
            the_winner = None

        g.previous_winners.append(the_winner.id)
        g.save()

        channel = ctx.guild.get_channel(g.channel)

        await channel.send(f"**Reroll**\nThe new winner of the giveaway of **{g.name}** is {the_winner.mention}! Congratulations!")
        await ctx.send_success("Rerolled!")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="End a giveaway early.", permissions=slash_perms.admin_and_up())
    async def giveawayend(self, ctx: BlooContext, message_id: str):
        giveaway = guild_service.get_giveaway(_id=int(message_id))
        if giveaway is None:
            raise commands.BadArgument("A giveaway with that ID was not found.")
        elif giveaway.is_ended:
            raise commands.BadArgument("That giveaway has already ended.")
        
        ctx.tasks.tasks.remove_job(str(int(message_id) + 2), 'default')
        await end_giveaway(giveaway.channel, message_id, giveaway.winners)

        await ctx.send_success("Giveaway ended!")


    @tasks.loop(seconds=360)
    async def time_updater_loop(self):
        guild = self.bot.get_guild(cfg.guild_id)
        if guild is None:
            return

        giveaways = GiveawayDB.objects(is_ended=False)
        for giveaway in giveaways:
            await self.do_giveaway_update(giveaway, guild)

    
    async def do_giveaway_update(self, giveaway: GiveawayDB, guild: discord.Guild):
        if giveaway is None:
            return
        if giveaway.is_ended:
            return

        now = datetime.datetime.now()
        end_time = giveaway.end_time
        if end_time is None or end_time < now:
            return
        
        channel = guild.get_channel(giveaway.channel)

        # caching mechanism for each giveaway message so we don't get ratelimited by discord
        if giveaway._id in self.giveaway_messages:
            message = self.giveaway_messages[giveaway._id]
        else:
            try:
                message = await channel.fetch_message(giveaway._id)
                self.giveaway_messages[giveaway._id] = message
            except Exception:
                return

        if len(message.embeds) == 0:
            return
        
        embed = message.embeds[0]
        embed.set_field_at(0, name="Time remaining", value=f"Less than {humanize.naturaldelta(end_time - now)}")
        await message.edit(embed=embed)

    @time_updater_loop.error
    @giveawaystart.error
    @giveawayreroll.error
    @giveawayend.error
    async def info_error(self,  ctx: BlooContext, error):
        if isinstance(error, ApplicationCommandInvokeError):
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
    bot.add_cog(Giveaway(bot))
