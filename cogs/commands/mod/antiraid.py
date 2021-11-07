import traceback

import discord
from discord import guild
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from discord.commands import Option, slash_command
from discord.ext import commands
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.checks import PermissionsFailure, admin_and_up, mod_and_up
from utils.permissions.slash_perms import slash_perms


class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Add a phrase to the raid filter.", permissions=slash_perms.mod_and_up())
    async def raid(self, ctx: BlooContext, phrase: Option(str, description="Phrase to add")) -> None:
        """Add a phrase to the raid filter.

        Example usage
        --------------
        !raid <phrase>

        Parameters
        ----------
        phrase : str
            "Phrase to add"
        """

        # these are phrases that when said by a whitename, automatically bans them.
        # for example: known scam URLs
        done = guild_service.add_raid_phrase(phrase)
        if not done:
            raise commands.BadArgument("That phrase is already in the list.")
        else:
            await ctx.send_success(description=f"Added `{phrase}` to the raid phrase list!")

    # @admin_and_up()
    # @slash_command(guild_ids=[cfg.guild_id], description="Add a list of (newline-separated) phrases to the raid filter.", permissions=slash_perms.mod_and_up())
    # async def batchraid(self, ctx: BlooContext, *, phrases: str) -> None:
    #     """Add a list of (newline-separated) phrases to the raid filter.

    #     Example usage
    #     --------------
    #     !raid <phrase>

    #     Parameters
    #     ----------
    #     phrases : str
    #         "Phrases to add, separated with enter"
    #     """

    #     async with ctx.typing():
    #         phrases = list(set(phrases.split("\n")))
    #         phrases = [phrase.strip() for phrase in phrases]

    #         phrases_contenders = set(phrases)
    #         phrases_already_in_db = set([phrase.word for phrase in ctx.settings.guild().raid_phrases])

    #         duplicate_count = len(phrases_already_in_db & phrases_contenders) # count how many duplicates we have
    #         new_phrases = list(phrases_contenders - phrases_already_in_db)

    #     if not new_phrases:
    #         raise commands.BadArgument("All the phrases you supplied are already in the database.")

    #     phrases_prompt_string = "\n".join([f"**{i+1}**. {phrase}" for i, phrase in enumerate(new_phrases)])
    #     if len(phrases_prompt_string) > 3900:
    #         phrases_prompt_string = phrases_prompt_string[:3500] + "\n... (and some more)"

    #     embed = Embed(title="Confirm raidphrase batch",
    #                 color=discord.Color.dark_orange(),
    #                 description=f"{phrases_prompt_string}\n\nShould we add these {len(new_phrases)} phrases?")

    #     if duplicate_count > 0:
    #         embed.set_footer(text=f"Note: we found {duplicate_count} duplicates in your list.")

    #     message = await ctx.send(embed=embed)

    #     prompt_data = context.PromptDataReaction(message=message, reactions=['✅', '❌'], timeout=120, delete_after=True)
    #     response, _ = await ctx.prompt_reaction(info=prompt_data)

    #     if response == '✅':
    #         async with ctx.typing():
    #             for phrase in new_phrases:
    #                 await ctx.settings.add_raid_phrase(phrase)

    #         await ctx.send_success(f"Added {len(new_phrases)} phrases to the raid filter.", delete_after=5)
    #     else:
    #         await ctx.send_warning("Cancelled.", delete_after=5)

    #     await ctx.message.delete(delay=5)

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Remove a phrase from the raid filter.", permissions=slash_perms.mod_and_up())
    async def removeraid(self, ctx: BlooContext, phrase: Option(str, description="Phrase to remove")) -> None:
        """Remove a phrase from the raid filter.

        Example usage
        --------------
        !removeraid <phrase>

        Parameters
        ----------
        phrase : str
            "Phrase to remove"
        """

        word = phrase.lower()

        words = guild_service.get_guild().raid_phrases
        words = list(filter(lambda w: w.word.lower() == word.lower(), words))

        if len(words) > 0:
            guild_service.remove_raid_phrase(words[0].word)
            await ctx.send_success("Deleted!")
        else:
            raise commands.BadArgument("That word is not a raid phrase.")

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Toggle banning of *today's* new accounts in join spam detector.", permissions=slash_perms.mod_and_up())
    async def spammode(self, ctx: BlooContext, mode: Option(bool, description="True if you don't want to ban, False otherwise", required=False) = None) -> None:
        """Toggle banning of *today's* new accounts in join spam detector.

        Example usage
        --------------
        !spammode true
        """

        if mode is None:
            mode = not guild_service.get_guild().ban_today_spam_accounts

        guild_service.set_spam_mode(mode)
        await ctx.send_success(description=f"We {'**will ban**' if mode else 'will **not ban**'} accounts created today in join spam filter.")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Verify a user so they won't be banned by antiraid filters.", permissions=slash_perms.admin_and_up())
    async def verify(self, ctx: BlooContext, user: Option(discord.Member, description="User to verify"), mode: Option(bool, required=False) = None) -> None:
        """Verify a user so they won't be banned by antiraid filters.

        Example usage
        --------------
        !verify @user
        !verify @user true/false
        """

        profile = user_service.get_user(user.id)
        if mode is None:
            profile.raid_verified = not profile.raid_verified
        else:
            profile.raid_verified = mode

        profile.save()

        await ctx.send_success(description=f"{'**Verified**' if profile.raid_verified else '**Unverified**'} user {user.mention}.")

    @verify.error
    @spammode.error
    @removeraid.error
    # @batchraid.error
    @raid.error
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
            traceback.print_exc()


def setup(bot):
    bot.add_cog(AntiRaid(bot))
