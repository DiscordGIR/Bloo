import typing
import discord
from discord.ext import commands
from discord.commands.commands import Option, SlashCommand, SlashCommandGroup, slash_command
from discord.commands.context import AutocompleteContext

import traceback
from data.services.guild_service import guild_service
from utils.logger import logger
from utils.config import cfg
from utils.context import BlooContext
from utils.permissions.checks import PermissionsFailure, whisper
from utils.permissions.permissions import permissions

async def commands_list(ctx: AutocompleteContext):
    res = []
    for cog in ctx.bot.cogs:
        for command in ctx.bot.cogs[cog].get_commands():
            if isinstance(command, discord.MessageCommand) or isinstance(command, discord.UserCommand):
                continue
            elif isinstance(command, SlashCommandGroup):
                for sub_command in command.subcommands:
                    if ctx.value.lower() in f"{command.name} {sub_command.name}":
                        res.append(f"{command.name} {sub_command.name}")
            else:
                if ctx.value.lower() in command.name:
                    res.append(command.name.lower())

    res.sort()
    return res

class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.left_col_length = 17
        self.right_col_length = 80
        self.mod_only = ["ModActions", "ModUtils", "Filters", "BoosterEmojis", "RoleAssignButtons", "Giveaway", "Admin", "AntiRaid", "Trivia"]
        self.genius_only = ["Genius"]

    @slash_command(description="View all my cogs and commands.")
    async def help(self, ctx: BlooContext, *, commandname: Option(str, autocomplete=commands_list, required=False)):
        """Gets all my cogs and commands."""

        if not commandname:
            await ctx.respond('📬', ephemeral=True)
            header = "Get a detailed description for a specific command with `/help <command name>`\n"
            string = ""
            for cog_name in self.bot.cogs:
                cog = self.bot.cogs[cog_name]
                is_admin = permissions.has(ctx.guild, ctx.author, 6)
                is_mod = permissions.has(ctx.guild, ctx.author, 5)
                is_genius = permissions.has(ctx.guild, ctx.author, 4)
                submod = ctx.guild.get_role(guild_service.get_guild().role_sub_mod)
                
                if not cog.get_commands() or (cog_name in self.mod_only and not is_mod):
                    continue
                elif not cog.get_commands() or (cog_name in self.genius_only and not is_genius):
                    continue
                elif cog_name == "SubNews" and not (submod in ctx.author.roles or is_admin):
                    continue
                
                string += f"== {cog_name} ==\n"

                for command in cog.get_commands():
                    if isinstance(command, discord.MessageCommand) or isinstance(command, discord.UserCommand):
                        continue
                    command: typing.Union[SlashCommand, SlashCommandGroup] = command
                    spaces_left = ' ' * (self.left_col_length - len(command.name))
                    if command.description is not None:
                        command.brief = command.description.split("\n")[0]
                    else:
                        command.brief = "No description."
                    cmd_desc = command.brief[0:self.right_col_length] + "..." if len(command.brief) > self.right_col_length else command.brief

                    if isinstance(command, SlashCommandGroup):
                        string += f"\t* {command.name}{spaces_left} :: {cmd_desc}\n"
                        for c in command.subcommands:
                            spaces_left = ' ' * (self.left_col_length - len(c.name)-4)
                            if c.description is not None:
                                c.brief = c.description.split("\n")[0]
                            else:
                                c.brief = "No description."
                            cmd_desc = c.brief[0:self.right_col_length] + "..." if len(c.brief) > self.right_col_length else c.brief
                            string += f"\t\t* {c.name}{spaces_left} :: {cmd_desc}\n"
                    else:
                        string += f"\t* {command.name}{spaces_left} :: {cmd_desc}\n"

                string += "\n"

            try:
                parts = string.split("\n")
                group_size = 25
                if len(parts) <= group_size:
                    await ctx.author.send(header + "\n```asciidoc\n" + "\n".join(parts[0:group_size]) + "```")
                else:
                    seen = 0
                    await ctx.author.send(header + "\n```asciidoc\n" + "\n".join(parts[seen:seen+group_size]) + "```")
                    seen += group_size
                    while seen < len(parts):
                        await ctx.author.send("```asciidoc\n" + "\n".join(parts[seen:seen+group_size]) + "```")
                        seen += group_size
                        
            except Exception:
                raise commands.BadArgument("I tried to DM you but couldn't. Make sure your DMs are enabled.")

        else:
            command = self.bot.get_application_command(commandname.lower())
            if command:
                await ctx.respond('📬', ephemeral=True)
                if command.cog.qualified_name in self.mod_only and not permissions.has(ctx.guild, ctx.author, 5):
                    raise commands.BadArgument("You don't have permission to view that command.")
                elif command.cog.qualified_name in self.genius_only and not permissions.has(ctx.guild, ctx.author, 4):
                    raise commands.BadArgument("You don't have permission to view that command.")
                else:
                    embed = await self.get_usage_embed(ctx, command)
                    try:
                        await ctx.author.send(embed=embed)
                    except Exception:
                        raise commands.BadArgument("I tried to DM you but couldn't. Make sure your DMs are enabled.")
            else:
                raise commands.BadArgument("Command not found.")


    @whisper()
    @slash_command(description="View usage of a command")
    async def usage(self, ctx: BlooContext, command_arg: Option(str, autocomplete=commands_list)):
        """Show usage of one command
        
        Example usage
        -------------
        !usage devices

        Parameters
        ----------
        command_arg : str
            "Name of command"
        """

        command_arg_split = command_arg.split()
        if len(command_arg_split) > 1:
            # TODO fix this
            main_command: SlashCommandGroup = self.bot.get_application_command(command_arg_split[0].lower())
            sub_commands = [sc for sc in main_command.subcommands if command_arg.lower() in f"{main_command.name} {sc.name}"]
            if not sub_commands:
                raise commands.BadArgument("Command not found.")
            command = sub_commands[0]
        else:
            command = self.bot.get_application_command(command_arg.lower())
            if not command:
                raise commands.BadArgument("Command not found.")

        embed = await self.get_usage_embed(ctx, command)
        await ctx.respond(embed=embed, ephemeral=ctx.whisper)

    async def get_usage_embed(self,  ctx: BlooContext, command: SlashCommand):
        if command.cog.qualified_name in self.mod_only and not permissions.has(ctx.guild, ctx.author, 5):
            raise commands.BadArgument("You don't have permission to view that command.")
        elif command.cog.qualified_name in self.genius_only and not permissions.has(ctx.guild, ctx.author, 4):
            raise commands.BadArgument("You don't have permission to view that command.")
        else:
            args = ""
            for thing in command.options:
                if not thing.required:
                    args += f"[{str(thing.name)}] "
                else:
                    args += f"<{str(thing.name)}> "

            if command.full_parent_name:
                embed = discord.Embed(title=f"/{command.full_parent_name} {command.name} {args}")
            else:
                embed = discord.Embed(title=f"/{command.name} {args}")
            
            embed.description = f"{command.description or 'No description.'}\n```hs\n"
            for option in command.options:
                embed.description += f"{str(option.name)}: {str(option.input_type).split('.')[1]}{', optional' if not option.required else ''}\n    \"{option.description}\"\n"
                
            embed.description += "```"
            embed.color = discord.Color.random()
            return embed

    @usage.error
    @help.error
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
    bot.add_cog(Utilities(bot))
