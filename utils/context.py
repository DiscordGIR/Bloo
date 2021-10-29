from discord.utils import MISSING
from discord.colour import Color
from discord.commands import context
from discord.embeds import Embed
from discord.ext.commands import BadArgument
from datetime import datetime, timedelta
import pytimeparse


class PromptData:
    def __init__(self, value_name, description, convertor, timeout=120, title="", reprompt=False, raw=False):
        self.value_name = value_name
        self.description = description
        self.convertor = convertor
        self.title = title
        self.reprompt = reprompt
        self.timeout = timeout
        self.raw = raw
        
    def __copy__(self):
        return PromptData(self.value_name, self.description, self.convertor, self.title, self.reprompt)


class GIRContext(context.ApplicationContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whisper = False

    async def respond_or_edit(self, *args, **kwargs):
        if self.interaction.response.is_done():
            del kwargs["ephemeral"]
            await self.edit(*args, **kwargs)
        else:
            await self.respond(*args, **kwargs)

    async def send_success(self, description: str, title: str = ""):
        embed = Embed(title=title, description=description,  color=Color.dark_green())
        await self.respond_or_edit(content="", embed=embed, ephemeral=self.whisper, view=MISSING)
    
    async def send_warning(self, description: str, title: str = ""):
        embed = Embed(title=title, description=description,  color=Color.orange())
        await self.respond_or_edit(content="", embed=embed, ephemeral=self.whisper, view=MISSING)
    
    async def send_error(self, description):
        embed = Embed(title=":(\nYour command ran into a problem", description=description,  color=Color.orange())
        await self.respond_or_edit(content="", embed=embed, ephemeral=self.whisper, view=MISSING)
        
    async def prompt(self, info: PromptData):
        def wait_check(m):
            return m.author == self.author and m.channel == self.channel
    
        ret = None
        embed = Embed(
            title=info.title if not info.reprompt else f"That wasn't a valid {info.value_name}. {info.title if info.title is not None else ''}",
            description=info.description,
            color=Color.blurple() if not info.reprompt else Color.orange())
        embed.set_footer(text="Send 'cancel' to cancel.")

        await self.respond_or_edit(embed=embed, ephemeral=True)
        try:
            response = await self.bot.wait_for('message', check=wait_check, timeout=info.timeout)
        except TimeoutError:
            return
        else:
            await response.delete()
            if response.content.lower() == "cancel":
                return
            elif not response.content:
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
                    if info.raw:
                        ret = await info.convertor(self, response.content), response
                    else:
                        ret = await info.convertor(self, response.content)
                    
        return ret
    
 