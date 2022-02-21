import random
import re
import traceback
from asyncio import Lock
from datetime import datetime
from io import BytesIO
from typing import List

import aiofiles
import aiohttp
import discord
import markovify
from psutil import users
from data.model.tag import Tag
from data.services.guild_service import guild_service
from discord.commands import Option, slash_command
from discord.ext import commands
from discord.ext.commands.cooldowns import CooldownMapping
from utils.autocompleters import memes_autocomplete
from utils.config import cfg
from utils.context import BlooContext, PromptData
from utils.logger import logger
from utils.message_cooldown import MessageTextBucket
from utils.mod.filter import find_triggered_filters, find_triggered_raid_phrases
from utils.permissions.checks import (PermissionsFailure, memed_and_up,
                                      mempro_and_up, mod_and_up, whisper)
from utils.permissions.permissions import permissions
from utils.permissions.slash_perms import slash_perms
from utils.views.menu import Menu


def format_meme_page(_, entries, current_page, all_pages):
    embed = discord.Embed(
        title=f'All memes', color=discord.Color.blurple())
    for meme in entries:
        desc = f"Added by: {meme.added_by_tag}\nUsed {meme.use_count} {'time' if meme.use_count == 1 else 'times'}"
        if meme.image.read() is not None:
            desc += "\nHas image attachment"
        embed.add_field(name=meme.name, value=desc)
    embed.set_footer(
        text=f"Page {current_page} of {len(all_pages)}")
    return embed


class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.meme_cooldown = CooldownMapping.from_cooldown(
            1, 5, MessageTextBucket.custom)
        self.res_cooldown = CooldownMapping.from_cooldown(
            1, 25, MessageTextBucket.custom)
        self.memegen_cooldown = CooldownMapping.from_cooldown(
            1, 25, MessageTextBucket.custom)
        self.markov_lock = Lock()

    @slash_command(guild_ids=[cfg.guild_id], description="Display a meme")
    async def meme(self, ctx: BlooContext, name: Option(str, description="Meme name", autocomplete=memes_autocomplete), user_to_mention: Option(discord.Member, description="User to mention in the response", required=False)):
        """Displays a meme.

        Example usage
        -------------
        /meme name:<memename>

        Parameters
        ----------
        name : str
            "Name of meme to display"

        """
        name = name.lower()
        meme = guild_service.get_meme(name)

        if meme is None:
            raise commands.BadArgument("That meme does not exist.")

        # run cooldown so meme can't be spammed
        bucket = self.meme_cooldown.get_bucket(meme.name)
        current = datetime.now().timestamp()
        # ratelimit only if the invoker is not a moderator
        if bucket.update_rate_limit(current) and not (permissions.has(ctx.guild, ctx.author, 5) or ctx.guild.get_role(guild_service.get_guild().role_sub_mod) in ctx.author.roles):
            raise commands.BadArgument("That meme is on cooldown.")

        # if the Meme has an image, add it to the embed
        file = meme.image.read()
        if file is not None:
            file = discord.File(BytesIO(
                file), filename="image.gif" if meme.image.content_type == "image/gif" else "image.png")

        if user_to_mention is not None:
            title = f"{user_to_mention.mention}, have a look at this funny meme! LOL!"
        else:
            title = None

        await ctx.respond(content=title, embed=await self.prepare_meme_embed(meme), file=file)

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="List all memes")
    async def memelist(self, ctx: BlooContext):
        """List all meemes
        """

        memes = sorted(guild_service.get_guild().memes,
                       key=lambda meme: meme.name)

        if len(memes) == 0:
            raise commands.BadArgument("There are no memes defined.")

        menu = Menu(ctx, memes, per_page=12,
                    page_formatter=format_meme_page, whisper=ctx.whisper)
        await menu.start()

    memes = discord.SlashCommandGroup("memes", "Interact with memes", guild_ids=[
                                      cfg.guild_id], permissions=slash_perms.mod_and_up())

    @mod_and_up()
    @memes.command(description="Add a new meme")
    async def add(self, ctx: BlooContext, name: str) -> None:
        """Add a meme. Optionally attach an image. (Genius only)

        Example usage
        -------------
        /memes add roblox

        Parameters
        ----------
        name : str
            "Name of the meme"

        """

        if not name.isalnum():
            raise commands.BadArgument("Meme name must be alphanumeric.")

        if len(name.split()) > 1:
            raise commands.BadArgument(
                "Meme names can't be longer than 1 word.")

        if (guild_service.get_meme(name.lower())) is not None:
            raise commands.BadArgument("Meme with that name already exists.")

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter the content of this meme, and optionally attach an image.",
            convertor=str,
            raw=True)
        res = await ctx.prompt(prompt)

        if res is None:
            return

        description, response = res
        # prepare meme data for database
        meme = Tag()
        meme.name = name.lower()
        meme.content = description
        meme.added_by_id = ctx.author.id
        meme.added_by_tag = str(ctx.author)

        # did the user want to attach an image to this meme?
        if len(response.attachments) > 0:
            # ensure the attached file is an image
            image = response.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")
            else:
                image = await image.read()
            # save image bytes
            meme.image.put(image, content_type=_type)

        # store meme in database
        guild_service.add_meme(meme)

        _file = meme.image.read()
        if _file is not None:
            _file = discord.File(BytesIO(
                _file), filename="image.gif" if meme.image.content_type == "image/gif" else "image.png")

        await ctx.respond(f"Added new meme!", file=_file or discord.utils.MISSING, embed=await self.prepare_meme_embed(meme))

    @mod_and_up()
    @memes.command(description="Edit an existing meme")
    async def edit(self, ctx: BlooContext, name: Option(str, autocomplete=memes_autocomplete)) -> None:
        """Edit a meme's body, optionally attach an image.

        Example usage
        -------------
        /editmeme roblox this would be the body

        Parameters
        ----------
        name : str
            "Name of meme to edit"
        """

        if len(name.split()) > 1:
            raise commands.BadArgument(
                "Meme names can't be longer than 1 word.")

        name = name.lower()
        meme = guild_service.get_meme(name)

        if meme is None:
            raise commands.BadArgument("That meme does not exist.")

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="description",
            description="Please enter the content of this meme, and optionally attach an image.",
            convertor=str,
            raw=True)

        response = await ctx.prompt(prompt)
        if response is None:
            return

        description, response = response
        meme.content = description

        if len(response.attachments) > 0:
            # ensure the attached file is an image
            image = response.attachments[0]
            _type = image.content_type
            if _type not in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                raise commands.BadArgument("Attached file was not an image.")
            else:
                image = await image.read()

            # save image bytes
            if meme.image is not None:
                meme.image.replace(image, content_type=_type)
            else:
                meme.image.put(image, content_type=_type)
        else:
            meme.image.delete()

        if not guild_service.edit_meme(meme):
            raise commands.BadArgument("An error occurred editing that meme.")

        _file = meme.image.read()
        if _file is not None:
            _file = discord.File(BytesIO(
                _file), filename="image.gif" if meme.image.content_type == "image/gif" else "image.png")

        await ctx.respond(f"Meme edited!", file=_file or discord.utils.MISSING, embed=await self.prepare_meme_embed(meme))

    @mod_and_up()
    @memes.command(description="Delete a meme")
    async def delete(self, ctx: BlooContext, name: Option(str, description="Name of meme to delete", autocomplete=memes_autocomplete)):
        """Delete meme (geniuses only)

        Example usage
        --------------
        /memes delete name:<memename>

        Parameters
        ----------
        name : str
            "Name of meme to delete"

        """

        name = name.lower()

        meme = guild_service.get_meme(name)
        if meme is None:
            raise commands.BadArgument("That meme does not exist.")

        if meme.image is not None:
            meme.image.delete()

        guild_service.remove_meme(name)
        await ctx.send_warning(f"Deleted meme `{meme.name}`.", delete_after=5)

    async def prepare_meme_embed(self, meme):
        """Given a meme object, prepare the appropriate embed for it

        Parameters
        ----------
        meme : Meme
            Meme object from database

        Returns
        -------
        discord.Embed
            The embed we want to send
        """
        embed = discord.Embed(title=meme.name)
        embed.description = meme.content
        embed.timestamp = meme.added_date
        embed.color = discord.Color.blue()

        if meme.image.read() is not None:
            embed.set_image(url="attachment://image.gif" if meme.image.content_type ==
                            "image/gif" else "attachment://image.png")
        embed.set_footer(
            text=f"Added by {meme.added_by_tag} | Used {meme.use_count} {'time' if meme.use_count == 1 else 'times'}")
        return embed

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Ooo magic", name="8ball")
    async def _8ball(self, ctx: BlooContext, question: Option(str, description="Question")) -> None:
        responses = ["As I see it, yes.", "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
                     "Don’t count on it.", "It is certain.", "It is decidedly so.", "Most likely.", "My reply is no.", "My sources say no.",
                     "Outlook not so good.", "Outlook good.", "Reply hazy, try again.", "Signs point to yes.", "Very doubtful.", "Without a doubt.",
                     "Yes.", "Yes – definitely.", "You may rely on it."]

        response = random.choice(responses)
        embed = discord.Embed(color=discord.Color.blurple())
        embed.add_field(name="Question", value=discord.utils.escape_markdown(
            question), inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @mempro_and_up()
    @slash_command(guild_ids=[cfg.guild_id], description="Ooo magic (image version)", permissions=slash_perms.mempro_and_up())
    async def neuralnet(self, ctx: BlooContext) -> None:
        if cfg.resnext_token is None:
            raise commands.BadArgument("ResNext token is not set up!")

        db_guild = guild_service.get_guild()
        is_mod = permissions.has(ctx.guild, ctx.author, 5)
        if ctx.channel.id not in [db_guild.channel_general, db_guild.channel_botspam] and not is_mod:
            raise commands.BadArgument(f"This command can't be used here.")

        if not is_mod:
            bucket = self.res_cooldown.get_bucket(ctx.guild.name)
            current = datetime.now().timestamp()
            # ratelimit only if the invoker is not a moderator
            if bucket.update_rate_limit(current):
                raise commands.BadArgument("That command is on cooldown.")

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="image",
            description="Please attach an image.",
            raw=True)

        something = await ctx.prompt(prompt)
        if something is None:
            return

        _, response = something

        if not response.attachments or response.attachments[0].content_type not in ["image/png", "image/jpeg", "image/webp"]:
            raise commands.BadArgument(
                "Attached file was not an image.")

        if response.attachments[0].size > 8_000_000:
            raise commands.BadArgument(
                "That image is too large to be processed.")

        async with ctx.typing():
            contents_before = await response.attachments[0].read()
            contents = BytesIO(contents_before)
            async with aiohttp.ClientSession(headers={"token": cfg.resnext_token}) as client:
                form = aiohttp.FormData()
                form.add_field(
                    "file", contents, content_type=response.attachments[0].content_type)
                async with client.post('https://resnext.slim.rocks/', data=form) as resp:
                    if resp.status == 200:
                        j = await resp.json()
                        embed = discord.Embed()
                        confidence = j.get('confidence')
                        confidence_percent = f"{confidence*100:.1f}%"
                        embed.description = f"image prediction: {j.get('classification')}\nconfidence: {confidence_percent}"
                        embed.set_footer(
                            text=f"Requested by {ctx.author} • /neuralnet • Processed in {j.get('process_time')}s")
                        embed.set_image(url="attachment://image.png")

                        if confidence < 0.25:
                            embed.color = discord.Color.red()
                        elif confidence < 0.5:
                            embed.color = discord.Color.yellow()
                        elif confidence < 0.75:
                            embed.color = discord.Color.orange()
                        else:
                            embed.color = discord.Color.green()

                        await ctx.send(embed=embed, file=discord.File(BytesIO(contents_before), filename="image.png"))
                    else:
                        raise commands.BadArgument(
                            "An error occurred classifying that image.")

    memegen = discord.SlashCommandGroup("memegen", "Generate memes", guild_ids=[
                                        cfg.guild_id], permissions=slash_perms.memed_and_up())

    @memed_and_up()
    @memegen.command(description="Meme generator")
    async def regular(self, ctx: BlooContext, top_text: str, bottom_text: str) -> None:
        if cfg.resnext_token is None:
            raise commands.BadArgument("ResNext token is not set up!")

        # ensure text is english characters only with regex
        if not re.match(r'^[\x20-\x7E]*$', top_text):
            raise commands.BadArgument("Top text can't have weird characters.")
        if not re.match(r'^[\x20-\x7E]*$', bottom_text):
            raise commands.BadArgument(
                "Bottom text can't have weird characters.")

        db_guild = guild_service.get_guild()
        is_mod = permissions.has(ctx.guild, ctx.author, 5)
        if ctx.channel.id not in [db_guild.channel_general, db_guild.channel_botspam] and not is_mod:
            raise commands.BadArgument(f"This command can't be used here.")

        if not is_mod:
            bucket = self.memegen_cooldown.get_bucket(ctx.guild.name)
            current = datetime.now().timestamp()
            # ratelimit only if the invoker is not a moderator
            if bucket.update_rate_limit(current):
                raise commands.BadArgument("That command is on cooldown.")

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="image",
            description="Please attach an image.",
            raw=True)

        something = await ctx.prompt(prompt)
        if something is None:
            return

        _, response = something

        if not response.attachments or response.attachments[0].content_type not in ["image/png", "image/jpeg", "image/webp"]:
            raise commands.BadArgument(
                "Attached file was not an image.")

        if response.attachments[0].size > 8_000_000:
            raise commands.BadArgument(
                "That image is too large to be processed.")

        async with ctx.typing():
            contents_before = await response.attachments[0].read()
            contents = BytesIO(contents_before)
            async with aiohttp.ClientSession(headers={"token": cfg.resnext_token}) as client:
                form = aiohttp.FormData()
                form.add_field(
                    "file", contents, content_type=response.attachments[0].content_type)
                async with client.post(f'https://resnext.slim.rocks/meme?top_text={top_text}&bottom_text={bottom_text}', data=form) as resp:
                    if resp.status == 200:
                        resp = await resp.read()
                        embed = discord.Embed()
                        embed.set_footer(
                            text=f"Requested by {ctx.author} • /memegen")
                        embed.set_image(url="attachment://image.png")
                        embed.color = discord.Color.random()

                        await ctx.send(embed=embed, file=discord.File(BytesIO(resp), filename="image.png"))
                    else:
                        raise commands.BadArgument(
                            "An error occurred generating that meme.")

    @memed_and_up()
    @memegen.command(description="Motivational poster)")
    async def motivate(self, ctx: BlooContext, top_text: str, bottom_text: str) -> None:
        if cfg.resnext_token is None:
            raise commands.BadArgument("ResNext token is not set up!")

        # ensure text is english characters only with regex
        if not re.match(r'^[\x20-\x7E]*$', top_text):
            raise commands.BadArgument("Top text can't have weird characters.")
        if not re.match(r'^[\x20-\x7E]*$', bottom_text):
            raise commands.BadArgument(
                "Bottom text can't have weird characters.")

        db_guild = guild_service.get_guild()
        is_mod = permissions.has(ctx.guild, ctx.author, 5)
        if ctx.channel.id not in [db_guild.channel_general, db_guild.channel_botspam] and not is_mod:
            raise commands.BadArgument(f"This command can't be used here.")

        if not is_mod:
            bucket = self.memegen_cooldown.get_bucket(ctx.guild.name)
            current = datetime.now().timestamp()
            # ratelimit only if the invoker is not a moderator
            if bucket.update_rate_limit(current):
                raise commands.BadArgument("That command is on cooldown.")

        await ctx.defer(ephemeral=True)
        prompt = PromptData(
            value_name="image",
            description="Please attach an image.",
            raw=True)

        something = await ctx.prompt(prompt)
        if something is None:
            return

        _, response = something

        if not response.attachments or response.attachments[0].content_type not in ["image/png", "image/jpeg", "image/webp"]:
            raise commands.BadArgument(
                "Attached file was not an image.")

        if response.attachments[0].size > 8_000_000:
            raise commands.BadArgument(
                "That image is too large to be processed.")

        async with ctx.typing():
            contents_before = await response.attachments[0].read()
            contents = BytesIO(contents_before)
            async with aiohttp.ClientSession(headers={"token": cfg.resnext_token}) as client:
                form = aiohttp.FormData()
                form.add_field(
                    "file", contents, content_type=response.attachments[0].content_type)
                async with client.post(f'https://resnext.slim.rocks/demotivational-meme?top_text={top_text}&bottom_text={bottom_text}', data=form) as resp:
                    if resp.status == 200:
                        resp = await resp.read()
                        embed = discord.Embed()
                        embed.set_footer(
                            text=f"Requested by {ctx.author} • /memegen")
                        embed.set_image(url="attachment://image.png")
                        embed.color = discord.Color.random()

                        await ctx.send(embed=embed, file=discord.File(BytesIO(resp), filename="image.png"))
                    else:
                        raise commands.BadArgument(
                            "An error occurred generating that meme.")

    @memed_and_up()
    @memegen.command(description="AI generated text from chat history")
    async def text(self, ctx):
        if not cfg.markov_enabled:
            raise commands.BadArgument("Markov is not enabled in the bot's config.")

        db_guild = guild_service.get_guild()
        is_mod = permissions.has(ctx.guild, ctx.author, 5)
        if ctx.channel.id not in [db_guild.channel_general, db_guild.channel_botspam] and not is_mod:
            raise commands.BadArgument(f"This command can't be used here.")

        if not is_mod:
            bucket = self.memegen_cooldown.get_bucket(ctx.guild.name)
            current = datetime.now().timestamp()
            # ratelimit only if the invoker is not a moderator
            if bucket.update_rate_limit(current):
                raise commands.BadArgument("That command is on cooldown.")

        async with aiofiles.open("bloo_ai.txt", mode="r") as f:
            lines = await f.read()
        lines = lines.split("\n")
        if not lines:
            return

        text_model = markovify.Text(lines)
        for _ in range(5):
            word = text_model.make_sentence()
            if word:
                await ctx.respond(word, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))
                return
        
        raise commands.BadArgument("Failed to generate some text. The text model probably isn't big enough yet...")

    @memed_and_up()
    @memegen.command(description="AI generated text from chat history, demotivational meme format")
    async def aipfp(self, ctx, member: Option(discord.Member, description="Whose profile picture to use")):
        if not cfg.markov_enabled:
            raise commands.BadArgument("Markov is not enabled in the bot's config.")
        if cfg.resnext_token is None:
            raise commands.BadArgument("ResNext token is not set up!")
        member: discord.Member = member
        if member.display_avatar is None:
            raise commands.BadArgument("That member doesn't have an avatar set.")

        db_guild = guild_service.get_guild()
        is_mod = permissions.has(ctx.guild, ctx.author, 5)
        if ctx.channel.id not in [db_guild.channel_general, db_guild.channel_botspam] and not is_mod:
            raise commands.BadArgument(f"This command can't be used here.")

        if not is_mod:
            bucket = self.memegen_cooldown.get_bucket(ctx.guild.name)
            current = datetime.now().timestamp()
            # ratelimit only if the invoker is not a moderator
            if bucket.update_rate_limit(current):
                raise commands.BadArgument("That command is on cooldown.")

        async with aiofiles.open("bloo_ai.txt", mode="r") as f:
            lines = await f.read()
        lines = lines.split("\n")
        if not lines:
            return

        text_model = markovify.Text(lines)
        for _ in range(5):
            sentence_1 = text_model.make_sentence()
            while sentence_1 and not re.match(r'^[\x20-\x7E]*$', sentence_1):
                sentence_1 = text_model.make_sentence()

            sentence_2 = text_model.make_sentence()
            while sentence_2 and not re.match(r'^[\x20-\x7E]*$', sentence_2):
                sentence_2 = text_model.make_sentence()
            
            if sentence_1 and sentence_2:
                break

        if not sentence_1 or not sentence_2:
            raise commands.BadArgument("Failed to generate some text. The text model probably isn't big enough yet...")

        await ctx.defer(ephemeral=False)
        contents_before = await member.display_avatar.with_format("png").with_size(4096).read()
        contents = BytesIO(contents_before)
        async with aiohttp.ClientSession(headers={"token": cfg.resnext_token}) as client:
            form = aiohttp.FormData()
            form.add_field(
                "file", contents, content_type="image/png")
            
            async with client.post(f'https://resnext.slim.rocks/demotivational-meme?top_text={sentence_1}&bottom_text={sentence_2}', data=form) as resp:
                if resp.status == 200:
                    resp = await resp.read()
                    embed = discord.Embed()
                    embed.set_footer(
                        text=f"Requested by {ctx.author} • /memegen")
                    embed.set_image(url="attachment://image.png")
                    embed.color = discord.Color.random()

                    await ctx.respond(embed=embed, file=discord.File(BytesIO(resp), filename="image.png"))
                else:
                    raise commands.BadArgument(
                        "An error occurred generating that meme. The image is probably too small.")


    @memed_and_up()
    @memegen.command(description="AI generated text based on a prompt")
    async def aitext(self, ctx: BlooContext, prompt: Option(str, description="Text to base results on")):
        if cfg.open_ai_token is None:
            raise commands.BadArgument("This command is disabled.")

        db_guild = guild_service.get_guild()
        is_mod = permissions.has(ctx.guild, ctx.author, 5)
        if ctx.channel.id not in [db_guild.channel_general, db_guild.channel_botspam] and not is_mod:
            raise commands.BadArgument(f"This command can't be used here.")

        if not is_mod:
            bucket = self.memegen_cooldown.get_bucket(ctx.guild.name)
            current = datetime.now().timestamp()
            # ratelimit only if the invoker is not a moderator
            if bucket.update_rate_limit(current):
                raise commands.BadArgument("That command is on cooldown.")

        await ctx.defer(ephemeral=False)
        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {cfg.open_ai_token}", "Content-Type": "application/json"}) as client:
            async with client.post(f"https://api.openai.com/v1/engines/text-ada-001/completions", json={
                "prompt": prompt,
                "temperature": 0.7,
                "max_tokens": 64,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
                }) as resp:

                if resp.status == 200:
                    data = await resp.json()
                    text = data.get("choices")[0].get("text")
                    if find_triggered_filters(text, ctx.author) or find_triggered_raid_phrases(text, ctx.author):
                        raise commands.BadArgument("An OpenAI API error occured.")

                    await ctx.respond(text, allowed_mentions=discord.AllowedMentions(users=False, roles=False, everyone=False))
                else:
                    raise commands.BadArgument("An OpenAI API error occured.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not cfg.markov_enabled:
            return
        if message.guild is None:
            return
        if message.guild.id != cfg.guild_id:
            return
        db_guild = guild_service.get_guild()
        if message.channel.id not in [db_guild.channel_general, db_guild.channel_jailbreak]:
            return
        if not message.content or len(message.content) < 4:
            return
        if message.author.bot:
            return
        if re.search(r'((https|http)?://\S+)', message.content):
            return

        if find_triggered_filters(message.content, message.author) or find_triggered_raid_phrases(message.content, message.author):
            return

        async with self.markov_lock:
            async with aiofiles.open("bloo_ai.txt", mode="a+") as f:
                await f.seek(0)
                lines = await f.read()
                if not lines:
                    lines = []
                else:
                    lines = lines.split("\n")

                if len(lines) > 50_000:
                    lines_to_write = lines[-50_000:]
                    lines_to_write.append(message.content)
                elif not lines:
                    lines_to_write = [message.content]
                else:
                    lines_to_write = lines + [message.content]

            async with aiofiles.open("bloo_ai.txt", mode="w") as f:
                await f.write("\n".join(lines_to_write))

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not cfg.markov_enabled:
            return
        if message.guild is None:
            return
        if message.guild.id != cfg.guild_id:
            return
        db_guild = guild_service.get_guild()
        if message.channel.id not in [db_guild.channel_general, db_guild.channel_jailbreak]:
            return
        if not message.content or len(message.content) < 4:
            return
        if message.author.bot:
            return
        if re.search(r'((https|http)?://\S+)', message.content):
            return

        removed = False
        async with self.markov_lock:
            async with aiofiles.open("bloo_ai.txt", mode="a+") as f:
                await f.seek(0)
                lines = await f.read()
                if not lines:
                    lines = []
                else:
                    lines = lines.split("\n")

                while message.content in lines:
                    removed = True
                    lines.remove(message.content)

            if removed:
                async with aiofiles.open("bloo_ai.txt", mode="w") as f:
                    await f.write("\n".join(lines))

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: List[discord.Message]):
        if not cfg.markov_enabled:
            return
        if messages[0].guild is None:
            return
        if messages[0].guild.id != cfg.guild_id:
            return
        db_guild = guild_service.get_guild()

        removed = False
        async with self.markov_lock:
            async with aiofiles.open("bloo_ai.txt", mode="a+") as f:
                await f.seek(0)
                lines = await f.read()
                if not lines:
                    lines = []
                else:
                    lines = lines.split("\n")

                for message in messages:
                    if not message.content or len(message.content) < 4:
                        continue
                    if message.author.bot:
                        continue
                    if message.channel.id not in [db_guild.channel_general, db_guild.channel_jailbreak]:
                        return
                    if re.search(r'((https|http)?://\S+)', message.content):
                        continue

                    while message.content in lines:
                        removed = True
                        lines.remove(message.content)

            if removed:
                async with aiofiles.open("bloo_ai.txt", mode="w") as f:
                    await f.write("\n".join(lines))

    @text.error
    @aipfp.error
    @aitext.error
    @_8ball.error
    @regular.error
    @motivate.error
    @neuralnet.error
    @edit.error
    @meme.error
    @memelist.error
    @delete.error
    @add.error
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
    bot.add_cog(Memes(bot))
