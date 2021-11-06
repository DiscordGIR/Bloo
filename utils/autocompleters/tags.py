from discord.commands.context import AutocompleteContext
from data.services import guild_service


async def tags_autocomplete(ctx: AutocompleteContext):
    tags = [tag.name.lower() for tag in guild_service.get_guild().tags]
    tags.sort()
    tags = tags[:25]
    return [tag for tag in tags if tag.lower().startswith(ctx.value.lower())]
