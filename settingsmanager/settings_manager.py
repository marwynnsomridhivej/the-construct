from base import ManagerBase
from matchmanager import R6Map

from .enums import PER_GUILD_MAP_POOL_LIMIT
from .settings import CustomMapPool, SettingsWrapper

__all__ = ("SettingsManager",)


class SettingsManager(ManagerBase):
    """Database manager to manage settings-related data."""

    def __init__(self, settings_loc: str):
        super().__init__(settings_loc, "settings")

    async def load(self):
        """Create the ncessary directories and load into memory."""
        await super()._load(name="SettingsManager")

    async def get_or_create_wrapper(self) -> SettingsWrapper:
        """Get or create the SettingsWrapper.

        Returns:
            SettingsWrapper: The SettingsWrapper instance.
        """
        return await super()._get_or_create_wrapper(cls=SettingsWrapper)

    async def create_guild_settings(
        self, guild_id: int, new_only: bool = False
    ) -> None:
        """Create a new settings entry for the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            new_only (bool, optional): Whether or not to skip creation if an
                entry already exists. Defaults to False.
        """
        wrapper = await self.get_or_create_wrapper()
        if not new_only or wrapper.get(guild_id) is None:
            wrapper.get_or_create(guild_id)
            await self.write(wrapper)

    async def get_admins(self, guild_id: int, owner_id: int | None = None) -> list[int]:
        """Get a list of bot administrators for the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            owner_id (int | None, optional): The user ID of the guild owner.
                Defaults to None.

        Returns:
            list[int]: A list of user IDs of any user that has the bot
                administrator permission in the guild.
        """
        wrapper = await self.get_or_create_wrapper()
        admin_ids = wrapper.get_or_create(guild_id).admins
        if owner_id is not None and owner_id not in admin_ids:
            admin_ids.append(owner_id)
        return admin_ids

    async def set_admins(self, guild_id: int, user_ids: list[int]) -> None:
        """Set bot administrators for the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            user_ids (list[int]): A list of user IDs of users to be designated
                bot administrator.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).set_admins(user_ids)
        await self.write(wrapper)

    async def is_admin(self, guild_id: int, user_id: int) -> bool:
        """Check whether or not a user is considered a bot administrator in the
        specified guild.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The user ID of the user.

        Returns:
            bool: Whether or not the user is a bot administrator.
        """
        wrapper = await self.get_or_create_wrapper()
        return user_id in wrapper.get_or_create(guild_id).admins

    async def bind_text_channel(self, guild_id: int, _id: int) -> None:
        """Bind a text channel in the specified guild to be used as the parent
        for thread creation.

        Args:
            guild_id (int): The ID of the guild.
            _id (int): The channel ID of the text channel.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).bind_text_channel_id(_id)
        await self.write(wrapper)

    async def get_bound_text_channel_id(self, guild_id: int) -> int | None:
        """Get the bound text channel for the specified guild.

        Args:
            guild_id (int): The ID of the guild.

        Returns:
            int | None: The ID of the bound text channel, if set.
        """
        wrapper = await self.get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).text_channel_id

    async def can_create_map_pool(self, guild_id: int) -> bool:
        """Check if a custom map pool can be created in the specified guild.

        Args:
            guild_id (int): The ID of the guild.

        Returns:
            bool: Whether or not a custom map pool can be created.
        """
        wrapper = await self.get_or_create_wrapper()
        return len(wrapper.get_or_create(guild_id).map_pools) < PER_GUILD_MAP_POOL_LIMIT

    async def create_map_pool(
        self, guild_id: int, owner_id: int, name: str, maps: list[R6Map]
    ) -> CustomMapPool:
        """Create a custom map pool.

        Args:
            guild_id (int): The ID of the guild.
            owner_id (int): The user ID of the creator.
            name (str): The name of the custom map pool.
            maps (list[R6Map]): A list of maps in the custom map pool.

        Returns:
            CustomMapPool: The created CustomMapPool object.
        """
        wrapper = await self.get_or_create_wrapper()
        pool = wrapper.get_or_create(guild_id).create_map_pool(
            owner_id, name.lower(), maps
        )
        await self.write(wrapper)
        return pool

    async def get_map_pool(self, guild_id: int, name: str) -> CustomMapPool:
        """Get a custom map pool in the specified guild by name.

        Args:
            guild_id (int): The ID of the guild.
            name (str): The name of the custom map pool to search for.

        Returns:
            CustomMapPool: The found CustomMapPool object.
        """
        wrapper = await self.get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).get_map_pool(name)

    async def get_all_map_pools(self, guild_id: int) -> list[CustomMapPool]:
        """Get a list of all custom map pools in the specified guild.

        Args:
            guild_id (int): The ID of the guild.

        Returns:
            list[CustomMapPool]: A list of all custom map pools.
        """
        wrapper = await self.get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).map_pools

    async def delete_map_pool(self, guild_id: int, name: str) -> None:
        """Delete a custom map pool in the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            name (str): The name of the custom map pool to delete.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).delete_map_pool(name)
        await self.write(wrapper)

    async def name_map_pool(self, guild_id: int, old_name: str, new_name: str) -> None:
        """Set the name of a custom map pool in the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            old_name (str): The previous name.
            new_name (str): The new name.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).name_map_pool(old_name, new_name)
        await self.write(wrapper)

    async def modify_map_pool_maps(
        self, guild_id: int, name: str, maps: list[R6Map]
    ) -> None:
        """Modify what maps are in a custom map pool.

        Args:
            guild_id (int): The ID of the guild.
            name (str): The name of the custom map pool.
            maps (list[R6Map]): The list of maps to assign.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).modify_map_pool_maps(name, maps)
        await self.write(wrapper)
