from data.services.guild_service import guild_service


async def tags_autocomplete(_, value):
    tags = [tag.name.lower() for tag in guild_service.get_guild().tags]
    tags.sort()
    tags = tags[:25]
    return [tag for tag in tags if tag.lower().startswith(value.lower())]
