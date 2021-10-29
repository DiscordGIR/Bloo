from data.model.guild import Guild
from data.model.tag import Tag
from utils.config import cfg


class GuildService:
    def get_guild(self) -> Guild:
        """Returns the state of the main guild from the database.

        Returns
        -------
        Guild
            The Guild document object that holds information about the main guild.
        """

        return Guild.objects(_id=cfg.guild_id).first()
    
    def add_tag(self, tag: Tag) -> None:
        Guild.objects(_id=cfg.guild_id).update_one(push__tags=tag)

    def remove_tag(self, tag: str):
        return Guild.objects(_id=cfg.guild_id).update_one(pull__tags__name=Tag(name=tag).name)

    def edit_tag(self, tag):
        return Guild.objects(_id=cfg.guild_id, tags__name=tag.name).update_one(set__tags__S=tag)

    def get_tag(self, name: str):
        tag = Guild.objects.get(_id=cfg.guild_id).tags.filter(name=name).first()
        if tag is None:
            return
        tag.use_count += 1
        self.edit_tag(tag)
        return tag


guild_service = GuildService()