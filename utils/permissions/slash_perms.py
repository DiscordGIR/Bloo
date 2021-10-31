from typing import List
from utils.permissions.permissions import permissions
from discord.commands.permissions import Permission
from data.services.guild_service import guild_service


class SlashPerms:
    def memplus_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(1)

    def mempro_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(2)

    def memed_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(3)

    def genius_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(4)

    ####################
    # Staff Roles
    ####################

    def submod_or_admin_and_up(self) -> List[Permission]:
      return permissions.calculate_permissions(6) + [Permission(id=guild_service.get_guild().role_sub_mod, type=1, permission=True)]

    def genius_or_submod_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(4) + [Permission(id=guild_service.get_guild().role_sub_mod, type=1, permission=True)]

    def mod_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(5)

    def admin_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(6)

    ####################
    # Other
    ####################

    def guild_owner_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(7)

    def bot_owner_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(9)


slash_perms = SlashPerms()
