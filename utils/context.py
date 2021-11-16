import discord
from discord.ext import commands
from discord.ext.commands import BadArgument

import pytimeparse
import asyncio
from datetime import datetime, timedelta
from utils.tasks import Tasks

class PromptData:
    def __init__(self, value_name, description, convertor=None, timeout=120, title="", reprompt=False, raw=False):
        self.value_name = value_name
        self.description = description
        self.convertor = convertor
        self.title = title
        self.reprompt = reprompt
        self.timeout = timeout
        self.raw = raw
        
    def __copy__(self):
        return PromptData(self.value_name, self.description, self.convertor, self.title, self.reprompt)


class PromptDataReaction:
    def __init__(self, message, reactions, timeout=None, delete_after=False, raw_emoji=False):
        self.message = message
        self.reactions = reactions        
        self.timeout = timeout
        self.delete_after = delete_after
        self.raw_emoji = raw_emoji

class BlooContext(discord.context.ApplicationContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whisper = False
        self.tasks: Tasks = self.bot.tasks

    async def respond_or_edit(self, *args, **kwargs):
        """Creates or edits an interaction response"""
        if self.interaction.response.is_done():
            if kwargs.get("ephemeral") is not None:
                del kwargs["ephemeral"]
            if kwargs.get("delete_after") is not None:
                del kwargs["delete_after"]
            return await self.edit(*args, **kwargs)
        else:
            if kwargs.get("view") is None:
                kwargs["view"] = discord.utils.MISSING
            return await self.respond(*args, **kwargs)

    async def send_success(self, description: str, title: str = ""):
        """Sends a success message
        
        Parameters
        ----------
        description : str
            "Success message"
        title : str
            "Success message title"

        """
        embed = discord.Embed(title=title, description=description,  color=discord.Color.dark_green())
        return await self.respond_or_edit(content="", embed=embed, ephemeral=self.whisper, view=None)
    
    async def send_warning(self, description: str, title: str = ""):
        """Sends a warning message
        
        Parameters
        ----------
        description : str
            "Warning message"
        title : str
            "Warning message title"

        """
        embed = discord.Embed(title=title, description=description,  color=discord.Color.orange())
        return await self.respond_or_edit(content="", embed=embed, ephemeral=self.whisper, view=None)
    
    async def send_error(self, description):
        """Sends an error message
        
        Parameters
        ----------
        description : str
            "Error message"
        title : str
            "Error message title"

        """
        embed = discord.Embed(title=":(\nYour command ran into a problem", description=description,  color=discord.Color.red())
        return await self.respond_or_edit(content="", embed=embed, ephemeral=True, view=None)
        
    async def prompt(self, info: PromptData):
        """Prompts for a response
        
        Parameters
        ----------
        info : PromptData
            "Prompt information"

        """
        def wait_check(m):
            return m.author == self.author and m.channel == self.channel
    
        ret = None
        embed = discord.Embed(title=info.title if not info.reprompt else f"That wasn't a valid {info.value_name}. {info.title if info.title is not None else ''}", description=info.description, color=discord.Color.blurple() if not info.reprompt else discord.Color.orange())
        embed.set_footer(text="Send 'cancel' to cancel.")

        await self.respond_or_edit(content="", embed=embed, ephemeral=True, view=None)
        try:
            response = await self.bot.wait_for('message', check=wait_check, timeout=info.timeout)
        except asyncio.TimeoutError:
            await self.send_warning("Timed out.")
        else:
            await response.delete()
            if response.content.lower() == "cancel":
                return
            elif not response.content and info.convertor is not None:
                info.reprompt = True
                return await self.prompt(info)
            else:
                if info.convertor in [str, int, pytimeparse.parse]:
                    try:
                        if info.raw:
                            ret = info.convertor(response.content), response
                        else:
                            ret = info.convertor(response.content)
                    except Exception:
                        ret = None
                    
                    if ret is None:
                        info.reprompt = True
                        return await self.prompt(info)

                    if info.convertor is pytimeparse.parse:
                        now = datetime.now()
                        time = now + timedelta(seconds=ret)
                        if time < now:
                            raise BadArgument("Time has to be in the future >:(")

                else:
                    if info.convertor is not None:
                        value = await info.convertor(self, response.content)
                    else:
                        value = None

                    if info.raw:
                        ret = value, response
                    else:
                        ret = value
                    
        return ret
    
    async def prompt_reaction(self, info: PromptDataReaction):
        """Prompts for a reaction
        
        Parameters
        ----------
        info : PromptDataReaction
            "Prompt data"
            
        """
        for reaction in info.reactions:
            await info.message.add_reaction(reaction)
            
        def wait_check(reaction, user):
            res = (user.id != self.bot.user.id
                and reaction.message.id == info.message.id)
            
            if info.reactions:
                res = res and str(reaction.emoji) in info.reactions
            
            return res
            
        if info.timeout is None:
            while True:
                try:
                    reaction, reactor = await self.bot.wait_for('reaction_add', timeout=300.0, check=wait_check)
                    if reaction is not None:
                        return str(reaction.emoji), reactor    
                except asyncio.TimeoutError:
                    if self.bot.report.pending_tasks.get(info.message.id) == "TERMINATE":
                        return "TERMINATE", None
        else:
            try:
                reaction, reactor = await self.bot.wait_for('reaction_add', timeout=info.timeout, check=wait_check)
            except asyncio.TimeoutError:
                try:
                    if info.delete_after:
                        await info.message.delete()
                    else:
                        await info.message.clear_reactions()
                    return None, None
                except Exception:
                    pass
            else:
                if info.delete_after:
                    await info.message.delete()
                else:
                    await info.message.clear_reactions()
                
                if not info.raw_emoji:
                    return str(reaction.emoji), reactor    
                else:
                    return reaction, reactor    


class BlooOldContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def prompt(self, info: PromptData):
        def wait_check(m):
            return m.author == self.author and m.channel == self.channel
    
        ret = None
        embed = discord.Embed(
            title=info.title if not info.reprompt else f"That wasn't a valid {info.value_name}. {info.title if info.title is not None else ''}",
            description=info.description,
            color=discord.Color.blurple() if not info.reprompt else discord.Color.orange())
        embed.set_footer(text="Send 'cancel' to cancel.")
        
        prompt_msg = await self.send(embed=embed)
        try:
            response = await self.bot.wait_for('message', check=wait_check, timeout=info.timeout)
        except asyncio.TimeoutError:
            await prompt_msg.delete()
            return
        else:
            await response.delete()
            await prompt_msg.delete()
            if response.content.lower() == "cancel":
                return
            elif not response.content:
                info.reprompt = True
                return await self.prompt(info)
            else:
                if info.convertor in [str, int, pytimeparse.parse]:
                    try:
                        ret = info.convertor(response.content)
                    except Exception:
                        ret = None
                    
                    if ret is None:
                        info.reprompt = True
                        return await self.prompt(info)

                    if info.convertor is pytimeparse.parse:
                        now = datetime.now()
                        time = now + timedelta(seconds=ret)
                        if time < now:
                            raise commands.BadArgument("Time has to be in the future >:(")

                else:
                    ret = await info.convertor(self, response.content)
                    
        return ret
    
    async def prompt_reaction(self, info: PromptDataReaction):
        for reaction in info.reactions:
            await info.message.add_reaction(reaction)
            
        def wait_check(reaction, user):
            res = (user.id != self.bot.user.id
                and reaction.message == info.message)
            
            if info.reactions:
                res = res and str(reaction.emoji) in info.reactions
            
            return res
            
        if info.timeout is None:
            while True:
                try:
                    reaction, reactor = await self.bot.wait_for('reaction_add', timeout=300.0, check=wait_check)
                    if reaction is not None:
                        return str(reaction.emoji), reactor    
                except asyncio.TimeoutError:
                    if self.bot.report.pending_tasks.get(info.message.id) == "TERMINATE":
                        return "TERMINATE", None
        else:
            try:
                reaction, reactor = await self.bot.wait_for('reaction_add', timeout=info.timeout, check=wait_check)
            except asyncio.TimeoutError:
                try:
                    if info.delete_after:
                        await info.message.delete()
                    else:
                        await info.message.clear_reactions()
                    return None, None
                except Exception:
                    pass
            else:
                if info.delete_after:
                    await info.message.delete()
                else:
                    await info.message.clear_reactions()
                
                if not info.raw_emoji:
                    return str(reaction.emoji), reactor    
                else:
                    return reaction, reactor    
        
    async def send_warning(self, description: str, title="", delete_after: int = None):
        return await self.reply(embed=discord.Embed(title=title, description=description, color=discord.Color.orange()), delete_after=delete_after)

    async def send_success(self, description: str, title="", delete_after: int = None):
        return await self.reply(embed=discord.Embed(title=title, description=description, color=discord.Color.dark_green()), delete_after=delete_after)
        
    async def send_error(self, error):
        embed = discord.Embed(title=":(\nYour command ran into a problem")
        embed.color = discord.Color.red()
        embed.description = str(error)
        await self.send(embed=embed, delete_after=8)
