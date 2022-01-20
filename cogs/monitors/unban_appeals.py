import traceback

import discord
from cogs.commands.info.userinfo import determine_emoji, pun_map
from data.services.guild_service import guild_service
from discord.ext import commands
from data.services.user_service import user_service
from utils.context import BlooContext
from utils.config import cfg
from discord.utils import format_dt


class UnbanAppeals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        if message.guild.id != cfg.unban_appeal_guild_id:
            return
        if not message.webhook_id:
            return
        if not message.embeds:
            return

        embed = message.embeds[0]
        unban_username = embed.fields[0].value
        unban_id = embed.fields[1].value

        try:
            unban_id_parsed = int(unban_id)
            appealer = await self.bot.fetch_user(unban_id_parsed)
        except:
            appealer = None

        thread = await message.create_thread(name=f"{unban_username} ({unban_id})")
        for mod in message.guild.get_role(cfg.unban_appeal_mod_role).members:
            await thread.add_user(mod)

        if appealer is not None:
            await thread.send(embed=await self.generate_userinfo(appealer))
            cases_embeds = await self.generate_cases(appealer)
            if cases_embeds is not None:
                for case_embed in cases_embeds:
                    await thread.send(embed=case_embed)
            else:
                await thread.send(embed=discord.Embed(color=discord.Color.green(), description="No cases found for this user."))
            if message.guild.get_member(appealer.id) is not None:
                await thread.send(f"✅ {appealer.mention} is in the unban appeals server!")
            else:
                await thread.send(f"❌ {appealer} did not join the unban appeals server!")
        else:
            await thread.send(f"❌ Hmm, I couldn't find {unban_username} ({unban_id}) from Discord's API. Maybe this is not a valid user!")

        await thread.send(unban_id)

        m = await thread.send(f"Please vote with whether or not you want to unban this user!", allowed_mentions=discord.AllowedMentions(roles=True))
        await m.add_reaction("🔺")
        await m.add_reaction("🔻")
        await m.add_reaction("❌")

    async def generate_userinfo(self, appealer: discord.User):
        results = user_service.get_user(appealer.id)

        embed = discord.Embed(title=f"User Information",
                              color=discord.Color.blue())
        embed.set_author(name=appealer)
        embed.set_thumbnail(url=appealer.display_avatar)
        embed.add_field(name="Username",
                        value=f'{appealer} ({appealer.mention})', inline=True)
        embed.add_field(
            name="Level", value=results.level if not results.is_clem else "CLEMMED", inline=True)
        embed.add_field(
            name="XP", value=results.xp if not results.is_clem else "CLEMMED", inline=True)
        embed.add_field(
            name="Punishments", value=f"{results.warn_points} warn points\n{len(user_service.get_cases(appealer.id).cases)} cases", inline=True)

        embed.add_field(name="Account creation date",
                        value=f"{format_dt(appealer.created_at, style='F')} ({format_dt(appealer.created_at, style='R')})", inline=True)
        return embed

    async def generate_cases(self, appealer: discord.User):
        results = user_service.get_cases(appealer.id)
        if not results.cases:
            return None
        cases = [case for case in results.cases if case._type != "UNMUTE"]
        # reverse so newest cases are first
        cases.reverse()

        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i:i + n]
        cases_chunks = list(chunks(cases, 10))

        embeds = []
        for i, entries in enumerate(cases_chunks):
            embed = discord.Embed(
                title=f'Cases - Page {i + 1}', color=discord.Color.blurple())
            embed.set_author(name=appealer, icon_url=appealer.display_avatar)
            for case in entries:
                timestamp = case.date
                formatted = f"{format_dt(timestamp, style='F')} ({format_dt(timestamp, style='R')})"
                if case._type == "WARN" or case._type == "LIFTWARN":
                    if case.lifted:
                        embed.add_field(
                            name=f'{determine_emoji(case._type)} Case #{case._id} [LIFTED]', value=f'**Points**: {case.punishment}\n**Reason**: {case.reason}\n**Lifted by**: {case.lifted_by_tag}\n**Lift reason**: {case.lifted_reason}\n**Warned on**: {formatted}', inline=True)
                    elif case._type == "LIFTWARN":
                        embed.add_field(name=f'{determine_emoji(case._type)} Case #{case._id} [LIFTED (legacy)]',
                                        value=f'**Points**: {case.punishment}\n**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Warned on**: {formatted}', inline=True)
                    else:
                        embed.add_field(name=f'{determine_emoji(case._type)} Case #{case._id}',
                                        value=f'**Points**: {case.punishment}\n**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Warned on**: {formatted}', inline=True)
                elif case._type == "MUTE" or case._type == "REMOVEPOINTS":
                    embed.add_field(name=f'{determine_emoji(case._type)} Case #{case._id}',
                                    value=f'**{pun_map[case._type]}**: {case.punishment}\n**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Time**: {formatted}', inline=True)
                elif case._type in pun_map:
                    embed.add_field(name=f'{determine_emoji(case._type)} Case #{case._id}',
                                    value=f'**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**{pun_map[case._type]} on**: {formatted}', inline=True)
                else:
                    embed.add_field(name=f'{determine_emoji(case._type)} Case #{case._id}',
                                    value=f'**Reason**: {case.reason}\n**Moderator**: {case.mod_tag}\n**Time**: {formatted}', inline=True)
            embeds.append(embed)
        return embeds


def setup(bot):
    if cfg.unban_appeal_guild_id is not None and cfg.unban_appeal_mod_role is not None:
        bot.add_cog(UnbanAppeals(bot))
