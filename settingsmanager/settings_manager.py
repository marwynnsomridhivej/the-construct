from typing import List, Union

from base import ManagerBase
from matchmanager import R6Map

from .enums import PER_GUILD_MAP_POOL_LIMIT
from .settings import CustomMapPool, SettingsWrapper

__all__ = ("SettingsManager",)


class SettingsManager(ManagerBase):
    def __init__(self, settings_loc: str):
        super().__init__(settings_loc, "settings")

    async def load(self):
        await super().load(name="SettingsManager")

    async def _get_or_create_wrapper(self) -> SettingsWrapper:
        return await super()._get_or_create_wrapper(cls=SettingsWrapper)

    async def create_guild_settings(
        self, guild_id: int, new_only: bool = False
    ) -> None:
        wrapper = await self._get_or_create_wrapper()
        if not new_only or wrapper.get(guild_id) is None:
            wrapper.get_or_create(guild_id)
            await self.write(wrapper)

    async def get_admins(self, guild_id: int, owner_id: int = None) -> List[int]:
        wrapper = await self._get_or_create_wrapper()
        admin_ids = wrapper.get_or_create(guild_id).admins
        if owner_id is not None and owner_id not in admin_ids:
            admin_ids.append(owner_id)
        return admin_ids

    async def set_admins(self, guild_id: int, user_ids: List[int]) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id).set_admins(user_ids)
        await self.write(wrapper)

    async def is_admin(self, guild_id: int, user_id: int) -> bool:
        wrapper = await self._get_or_create_wrapper()
        return user_id in wrapper.get_or_create(guild_id).admins

    async def bind_text_channel(self, guild_id: int, _id: int) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id).bind_text_channel_id(_id)
        await self.write(wrapper)

    async def get_bound_text_channel_id(self, guild_id: int) -> Union[int, None]:
        wrapper = await self._get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).text_channel_id

    async def can_create_map_pool(self, guild_id: int) -> bool:
        wrapper = await self._get_or_create_wrapper()
        return len(wrapper.get_or_create(guild_id).map_pools) < PER_GUILD_MAP_POOL_LIMIT

    async def create_map_pool(
        self, guild_id: int, owner_id: int, name: str, maps: List[R6Map]
    ) -> CustomMapPool:
        wrapper = await self._get_or_create_wrapper()
        pool = wrapper.get_or_create(guild_id).create_map_pool(
            owner_id, name.lower(), maps
        )
        await self.write(wrapper)
        return pool

    async def get_map_pool(self, guild_id: int, name: str) -> CustomMapPool:
        wrapper = await self._get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).get_map_pool(name)

    async def get_all_map_pools(self, guild_id: int) -> List[CustomMapPool]:
        wrapper = await self._get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).map_pools

    async def delete_map_pool(self, guild_id: int, name: str) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id).delete_map_pool(name)
        await self.write(wrapper)

    async def name_map_pool(self, guild_id: int, old_name: str, new_name: str) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id).name_map_pool(old_name, new_name)
        await self.write(wrapper)

    async def modify_map_pool_maps(
        self, guild_id: int, name: int, maps: List[R6Map]
    ) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id).modify_map_pool_maps(name, maps)
        await self.write(wrapper)
