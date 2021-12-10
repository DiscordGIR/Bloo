from collections import defaultdict
import discord
from discord.commands import Option, slash_command
from discord.ext import commands

import re
import traceback
from utils.logger import logger
from utils.autocompleters import device_autocomplete, get_ios_cfw, ios_on_device_autocomplete, transform_groups
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.checks import (PermissionsFailure, always_whisper, ensure_invokee_role_lower_than_bot, whisper)
from utils.views.devices import Confirm

class Devices(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.devices_test = re.compile(r'^.+ \[.+\,.+\]$')
        self.devices_remove_re = re.compile(r'\[.+\,.+\]$')
        self.possible_devices = ['iphone', 'ipod', 'ipad', 'homepod', 'apple']

    @ensure_invokee_role_lower_than_bot()
    @always_whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Add device to nickname")
    async def adddevice(self, ctx: BlooContext, device: Option(str, description="Name of your device", autocomplete=device_autocomplete), version: Option(str, description="Device OS version", autocomplete=ios_on_device_autocomplete)) -> None:
        """Add device name to your nickname, i.e `SlimShadyIAm [iPhone 12, 14.2]`. See /listdevices for valid device inputs.

        Example usage
        -------------
        /adddevice device:<devicename>

        Parameters
        ----------
        device : str
            "device user wants to set nickname to"

        """
        new_nick = ctx.author.display_name
        # check if user already has a device in their nick
        if re.match(self.devices_test, ctx.author.display_name):
            # they already have a device set
            view = Confirm(ctx, true_response="Alright, we'll swap your device!",
                           false_response="Cancelled adding device to your name.")
            await ctx.respond('You already have a device in your nickname. Would you like to replace it?', view=view, ephemeral=True)
            # Wait for the View to stop listening for input...
            await view.wait()
            change_name = view.value

            if change_name:
                # user wants to remove existing device, let's do that
                new_nick = re.sub(self.devices_remove_re, "",
                                  ctx.author.display_name).strip()
                if len(new_nick) > 32:
                    raise commands.BadArgument("Nickname too long")
            else:
                return

        response = await get_ios_cfw()
        device_groups = response.get("groups")

        transformed_groups = transform_groups(device_groups)
        devices = [group for group in transformed_groups if group.get(
            'name').lower() == device.lower() or device.lower() in [x.lower() for x in group.get('devices')]]

        if not devices:
            raise commands.BadArgument("No device found with that name.")

        matching_device = devices[0]
        board = devices[0].get("devices")[0]

        ios = response.get("ios")
        firmware = [v for v in ios if board in v.get(
            'devices') and version == v.get('version')]

        if not firmware:
            raise commands.BadArgument("No firmware found with that version.")

        firmware = firmware[0].get('version')
        # change the user's nickname!
        if firmware is not None:
            # name = matching_device["name"]
            # name = name.replace(' Plus', '+')
            # name = name.replace('Pro Max', 'PM')
            # # name = re.sub(r'\(?(\d\d?(\.\d)?\)?)-inch\)?', r'\1"', name)
            # name = re.sub(r' \(?\d+(\.\d+)?-inch\)?', "", name)
            # name = re.sub(r'\((\d+)(st|nd|rd|th) generation\)', r'\1', name)
            
            firmware = re.sub(r' beta (\d+)', r'b\1', firmware)
            detailed_device = response.get("device").get(matching_device.get("devices")[0])
            name = detailed_device["soc"]
            new_nick = f"{new_nick} [{name}, {firmware}]"

            if len(new_nick) > 32:
                raise commands.BadArgument(f"Discord's nickname character limit is 32. `{discord.utils.escape_markdown(new_nick)}` is too long.")

            await ctx.author.edit(nick=new_nick)
            await ctx.send_success(f"Changed your nickname to `{discord.utils.escape_markdown(new_nick)}`!")

    @ensure_invokee_role_lower_than_bot()
    @always_whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="Remove device from nickname")
    async def removedevice(self, ctx: BlooContext) -> None:
        """Removes device from your nickname

        Example usage
        -------------
        /removedevice

        """

        if not re.match(self.devices_test, ctx.author.display_name):
            raise commands.BadArgument("You don't have a device nickname set!")

        new_nick = re.sub(self.devices_remove_re, "",
                          ctx.author.display_name).strip()
        if len(new_nick) > 32:
            raise commands.BadArgument("Nickname too long")

        await ctx.author.edit(nick=new_nick)
        await ctx.send_success("Removed device from your nickname!")

    @whisper()
    @slash_command(guild_ids=[cfg.guild_id], description="List all devices you can set your nickname to")
    async def listdevices(self, ctx: BlooContext) -> None:
        """List all possible devices you can set your nickname to.

        Example usage
        -------------
        /listdevices
        
        """

        devices_dict = defaultdict(list)

        response = await get_ios_cfw()
        devices = response.get("groups")
        devices_transformed = transform_groups(devices)

        for device in devices_transformed:
            device_type = device.get("type")
            if device_type == "TV":
                devices_dict['Apple TV'].append(device)
            elif device_type == "Watch":
                devices_dict['Apple Watch'].append(device)
            elif device_type in ['iPad', 'Pro', 'Air', 'mini']:
                devices_dict['iPad'].append(device)
            else:
                devices_dict[device_type].append(device)

        embed = discord.Embed(title="Devices list")
        embed.color = discord.Color.blurple()
        for key, devices in devices_dict.items():
            devices.sort(key=lambda x: x.get('order'))
            devices = [device.get("name") for device in devices]
            embed.add_field(name=key, value=', '.join(
                devices), inline=False)

        embed.set_footer(text="Powered by https://ios.cfw.guide")
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    @removedevice.error
    @adddevice.error
    @listdevices.error
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
    bot.add_cog(Devices(bot))
