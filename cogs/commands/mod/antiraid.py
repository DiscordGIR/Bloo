import discord
from discord.commands import Option, slash_command
from discord.ext import commands

import traceback
from data.services.guild_service import guild_service
from data.services.user_service import user_service
from utils.config import cfg
from utils.logger import logger
from utils.context import BlooContext, PromptData
from utils.permissions.checks import PermissionsFailure, admin_and_up, mod_and_up
from utils.permissions.slash_perms import slash_perms
from utils.views.devices import Confirm


class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Add a phrase to the raid filter.", permissions=slash_perms.mod_and_up())
    async def raid(self, ctx: BlooContext, phrase: Option(str, description="Phrase to add")) -> None:
        """Adds a phrase to the raid filter.

        Example usage
        --------------
        /raid phrase:<phrase>

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
            await ctx.send_success(description=f"Added `{phrase}` to the raid phrase list!", delete_after=5)

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Add a list of (newline-separated) phrases to the raid filter.", permissions=slash_perms.admin_and_up())
    async def batchraid(self, ctx: BlooContext) -> None:
        """Add a list of (newline-separated) phrases to the raid filter.

        Example usage
        --------------
        /batchraid

        Parameters
        ----------
        phrases : str
            "Phrases to add, separated with enter"
        """

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter the list of things you want added to raid filter (separated by newlines).",
            convertor=str)

        phrases = await ctx.prompt(prompt)

        if phrases is None:
            await ctx.send_warning("Cancelled.")
            return

        async with ctx.typing():
            phrases = list(set(phrases.split("\n")))
            phrases = [phrase.strip() for phrase in phrases]

            phrases_contenders = set(phrases)
            phrases_already_in_db = set([phrase.word for phrase in guild_service.get_guild().raid_phrases])

            duplicate_count = len(phrases_already_in_db & phrases_contenders) # count how many duplicates we have
            new_phrases = list(phrases_contenders - phrases_already_in_db)

        if not new_phrases:
            raise commands.BadArgument("All the phrases you supplied are already in the database.")

        phrases_prompt_string = "\n".join([f"**{i+1}**. {phrase}" for i, phrase in enumerate(new_phrases)])
        if len(phrases_prompt_string) > 3900:
            phrases_prompt_string = phrases_prompt_string[:3500] + "\n... (and some more)"

        embed = discord.Embed(title="Confirm raidphrase batch",
                        color=discord.Color.dark_orange(),
                        description=f"{phrases_prompt_string}\n\nShould we add these {len(new_phrases)} phrases?")

        if duplicate_count > 0:
            embed.set_footer(text=f"Note: we found {duplicate_count} duplicates in your list.")

        view = Confirm(ctx)
        await ctx.respond_or_edit(embed=embed, view=view, ephemeral=True)
        await view.wait()
        do_add = view.value

        if do_add:
            async with ctx.typing():
                for phrase in new_phrases:
                    guild_service.add_raid_phrase(phrase)

            await ctx.send_success(f"Added {len(new_phrases)} phrases to the raid filter.")
        else:
            await ctx.send_warning("Cancelled.")

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Remove a phrase from the raid filter.", permissions=slash_perms.mod_and_up())
    async def removeraid(self, ctx: BlooContext, phrase: Option(str, description="Phrase to remove")) -> None:
        """Removes a phrase from the raid filter.

        Example usage
        --------------
        /removeraid phrase:<phrase>

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
            await ctx.send_success("Deleted!", delete_after=5)
        else:
            raise commands.BadArgument("That word is not a raid phrase.")

    @mod_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Toggle banning of *today's* new accounts in join spam detector.", permissions=slash_perms.mod_and_up())
    async def spammode(self, ctx: BlooContext, mode: Option(bool, description="True if you don't want to ban, False otherwise", required=False) = None) -> None:
        """Toggles banning of *today's* new accounts in join spam detector.

        Example usage
        --------------
        /spammode mode:<mode>
        
        Parameters
        ----------
        mode : bool
            "Should we ban today's new accounts in the join spam detector?"
            
        """

        if mode is None:
            mode = not guild_service.get_guild().ban_today_spam_accounts

        guild_service.set_spam_mode(mode)
        await ctx.send_success(description=f"We {'**will ban**' if mode else 'will **not ban**'} accounts created today in join spam filter.")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Verify a user so they won't be banned by antiraid filters.", permissions=slash_perms.admin_and_up())
    async def verify(self, ctx: BlooContext, user: Option(discord.Member, description="User to verify"), mode: Option(bool, required=False) = None) -> None:
        """Verifies a user so they won't be banned by antiraid filters.

        Example usage
        --------------
        /verify @user
        
        Parameters
        ----------
        user : discord.Member
            "User to verify"
        mode : bool, optional
            "Value to set this user's verification to"
            
        """

        profile = user_service.get_user(user.id)
        if mode is None:
            profile.raid_verified = not profile.raid_verified
        else:
            profile.raid_verified = mode

        profile.save()

        await ctx.send_success(description=f"{'**Verified**' if profile.raid_verified else '**Unverified**'} user {user.mention}.")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Lock a channel.", permissions=slash_perms.admin_and_up())
    async def lock(self,  ctx: BlooContext, channel: Option(discord.TextChannel, description="Channel to lock", required=False) = None):
        """Lock a channel (admin only)

        Example usage
        --------------
        /lock
        /lock #channel
            
        Parameters
        ----------
        channel : discord.TextChannel, optional
            "Channel to lock"
        """

        if channel is None:
            channel = ctx.channel
            
        if await self.lock_unlock_channel(ctx, channel, True) is not None:
            await ctx.send_success(f"Locked {channel.mention}!")
        else:
            raise commands.BadArgument(f"{channel.mention} already locked or my permissions are wrong.")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Unlock a channel.", permissions=slash_perms.admin_and_up())
    async def unlock(self,  ctx: BlooContext, channel: Option(discord.TextChannel, description="Channel to unlock", required=False)  = None):
        """Unlock a channel (admin only)

        Example usage
        --------------
        /unlock 
        /unlock #channel
            
        Parameters
        ----------
        channel : discord.TextChannel, optional
            "Channel to unlock"
        """

        if channel is None:
            channel = ctx.channel
            
        if await self.lock_unlock_channel(ctx, channel) is not None:
            await ctx.send_success(f"Unlocked {channel.mention}!")
        else:
            raise commands.BadArgument(f"{channel.mention} already unlocked or my permissions are wrong.")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Mark a channel as automatically freezable during a raid", permissions=slash_perms.admin_and_up())
    async def freezeable(self,  ctx: BlooContext, channel: Option(discord.TextChannel, description="Channel to mark freezeable", required=False) = None):
        """Mark a channel as automatically freezable during a raid (admin only)

        Parameters
        ----------
        channel : discord.TextChannel, optional
            "Channel to mark, current channel by default"
        """

        channel = channel or ctx.channel
        if channel.id in guild_service.get_locked_channels():
            raise commands.BadArgument("That channel is already lockable.")
        
        guild_service.add_locked_channels(channel.id)
        await ctx.send_success(f"Added {channel.mention} as lockable channel!")

    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Mark a channel as automatically not freezable during a raid", permissions=slash_perms.admin_and_up())
    async def unfreezeable(self,  ctx: BlooContext, channel: Option(discord.TextChannel, description="Channel to mark as not freezeable", required=False) = None):
        channel = channel or ctx.channel
        if channel.id not in guild_service.get_locked_channels():
            raise commands.BadArgument("That channel isn't already lockable.")
        
        guild_service.remove_locked_channels(channel.id)
        await ctx.send_success(f"Removed {channel.mention} as lockable channel!")
            
    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Freeze all channels", permissions=slash_perms.admin_and_up())
    async def freeze(self, ctx):
        """Freeze all channels (admin only)

        Example usage
        --------------
        /freeze
        """
        
        channels = guild_service.get_locked_channels()
        if not channels:
            raise commands.BadArgument("No freezeable channels! Set some using `/freezeable`.")
        
        locked = []
        await ctx.defer()
        for channel in channels:
            channel = ctx.guild.get_channel(channel)
            if channel is not None:
                if await self.lock_unlock_channel(ctx, channel, lock=True):
                    locked.append(channel)
        
        if locked:              
            await ctx.send_success(f"Locked {len(locked)} channels!")
        else:
            raise commands.BadArgument("Server is already locked or my permissions are wrong.")
        
    
    @admin_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Unfreeze all channels", permissions=slash_perms.admin_and_up())
    async def unfreeze(self, ctx):
        """Unreeze all channels (admin only)

        Example usage
        --------------
        /unfreeze
        """

        channels = guild_service.get_locked_channels()
        if not channels:
            raise commands.BadArgument("No unfreezeable channels! Set some using `/freezeable`.")
        
        unlocked = []
        await ctx.defer()
        for channel in channels:
            channel = ctx.guild.get_channel(channel)
            if channel is not None:
                if await self.lock_unlock_channel(ctx, channel, lock=None):
                    unlocked.append(channel)
        
        if unlocked:              
            await ctx.send_success(f"Unlocked {len(unlocked)} channels!")
        else:
            raise commands.BadArgument("Server is already unlocked or my permissions are wrong.")

    async def lock_unlock_channel(self,  ctx: BlooContext, channel, lock=None):
        db_guild = guild_service.get_guild()
        
        default_role = ctx.guild.default_role
        member_plus = ctx.guild.get_role(db_guild.role_memberplus)   
        
        default_perms = channel.overwrites_for(default_role)
        memberplus_perms = channel.overwrites_for(member_plus)

        if lock and default_perms.send_messages is None and memberplus_perms.send_messages is None:
            default_perms.send_messages = False
            memberplus_perms.send_messages = True
        elif lock is None and (not default_perms.send_messages) and memberplus_perms.send_messages:
            default_perms.send_messages = None
            memberplus_perms.send_messages = None
        else:
            return
        
        try:
            await channel.set_permissions(default_role, overwrite=default_perms, reason="Locked!" if lock else "Unlocked!")
            await channel.set_permissions(member_plus, overwrite=memberplus_perms, reason="Locked!" if lock else "Unlocked!")
            return True
        except Exception:
            return

    @lock.error
    @unlock.error
    @freezeable.error
    @unfreezeable.error
    @freeze.error
    @unfreeze.error
    @verify.error
    @spammode.error
    @removeraid.error
    @batchraid.error
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
            logger.error(traceback.format_exc())


def setup(bot):
    bot.add_cog(AntiRaid(bot))
