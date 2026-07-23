from datetime import datetime
from typing import Any, Generator

import discord

from base import WrapperBase
from exceptions import InvalidGuildID, MapPoolAlreadyExists, MapPoolNotFound
from matchmanager import R6Map

__all__ = (
    "SettingsWrapper",
    "SettingsEntry",
    "CustomMapPool",
)


class SettingsWrapper(WrapperBase):
    """Wrapper class that wraps settings related data from the database into
    a python object.
    """

    __slots__ = ("__data",)

    def __init__(self, data: dict):
        self.__data: dict[int, SettingsEntry] = {
            int(guild_id): SettingsEntry.parse(entry)
            for guild_id, entry in data.items()
        }

    def get(self, guild_id: int, throw: bool = False) -> "SettingsEntry | None":
        """Get a SettingsEntry of the specified guild.

        Args:
            guild_id (int): The ID of the guild.
            throw (bool, optional): Whether or not to throw an exception if a
                SettingsEntry is not found. Defaults to False.

        Raises:
            InvalidGuildID: No SettingsEntry exists for the specified guild.

        Returns:
            SettingsEntry | None: The SettingsEntry instance of the specified
                guild.
        """
        entry = self.__data.get(guild_id)
        if entry is None and throw:
            raise InvalidGuildID(guild_id)
        return entry

    def get_or_create(self, guild_id: int) -> "SettingsEntry":
        """Get or create a SettingsEntry for the specified guild.

        Args:
            guild_id (int): The ID of the guild.

        Returns:
            SettingsEntry: An existing SettingsEntry instance or a newly created
                blank instance.
        """
        entry = self.get(guild_id)
        if entry is None:
            entry = SettingsEntry.create_blank()
            self.__data[guild_id] = entry
        return entry

    @property
    def data(self) -> dict[int, "SettingsEntry"]:
        """Obtain python dictionary data.

        Returns:
            dict[int, SettingsEntry]: The underlying python dict object.
        """
        return self.__data

    def serialise(self) -> dict:
        """Convert SettingsWrapper instance representation into a dict.

        Returns:
            dict: Dictionary representation of the SettingsWrapper instance.
        """
        return {guild_id: entry.serialise() for guild_id, entry in self.__data.items()}


class SettingsEntry(WrapperBase):
    """Wrapper class that wraps guild specific settings data from the database
    into a python object.
    """

    __slots__ = (
        "__admins",
        "__text_channel_id",
        "__map_pools",
    )

    def __init__(self, data: dict):
        self.__admins: list[int] = data["admins"]
        self.__text_channel_id: int | None
        try:
            self.__text_channel_id = int(data["text_channel_id"])
        except TypeError:
            self.__text_channel_id = None
        self.__map_pools: list[CustomMapPool] = [
            CustomMapPool.parse(pool) for pool in data["map_pools"]
        ]

    @property
    def admins(self) -> list[int]:
        """A list of all designated bot administrators."""
        return self.__admins

    @property
    def text_channel_id(self) -> int | None:
        """The channel ID of the bound text channel."""
        return self.__text_channel_id

    @property
    def map_pools(self) -> list["CustomMapPool"]:
        """A list of all created custom map pools."""
        return self.__map_pools

    def set_admins(self, user_ids: list[int]) -> None:
        """Set guild members as bot administrators by user ID.

        Args:
            user_ids (list[int]): The user IDs to set as bot administrator.
        """
        self.__admins = user_ids

    def bind_text_channel_id(self, _id: int) -> None:
        """Set the bound text channel.

        Args:
            _id (int): The channel ID of the desired text channel.
        """
        self.__text_channel_id = _id

    def create_map_pool(
        self, owner_id: int, name: str, maps: list[R6Map] = []
    ) -> "CustomMapPool":
        """Create a custom map pool.

        Args:
            owner_id (int): The user ID of the bot administrator that initiated
                the creation of the custom map pool.
            name (str): The name of the custom map pool.
            maps (list[R6Map], optional): A list of maps included in the map
                pool. Defaults to empty list.

        Raises:
            MapPoolAlreadyExists: A map pool with the same name already exists
                in the guild.

        Returns:
            CustomMapPool: The newly created custom map pool.
        """
        name_taken = any([pool.name == name for pool in self.__map_pools])
        if name_taken:
            raise MapPoolAlreadyExists(name)
        pool = CustomMapPool.create(owner_id, name, maps)
        self.__map_pools.append(pool)
        return pool

    def get_map_pool(self, name: str) -> "CustomMapPool":
        """Get a custom map pool by name.

        Args:
            name (str): The name of the custom map pool to search for.

        Raises:
            MapPoolNotFound: No custom map pool was found with the specified
                name.

        Returns:
            CustomMapPool: The found custom map pool.
        """
        pool = discord.utils.find(lambda p: p.name == name, self.__map_pools)
        if pool is None:
            raise MapPoolNotFound(name)
        return pool

    def delete_map_pool(self, name: str) -> None:
        """Delete a custom map pool by name.

        Args:
            name (str): The name of the custom map pool.
        """
        pool = self.get_map_pool(name)
        self.__map_pools.remove(pool)

    def name_map_pool(self, old_name: str, new_name: str) -> None:
        """Set the name of a custom map pool.

        Args:
            old_name (str): The current name.
            new_name (str): The desired name.

        Raises:
            MapPoolAlreadyExists: Another custom map pool already has the
                specified name.
        """
        pool = self.get_map_pool(old_name)
        try:
            self.get_map_pool(new_name)
        except MapPoolNotFound:
            pool.set_name(new_name)
        else:
            raise MapPoolAlreadyExists(new_name)

    def modify_map_pool_maps(self, name: str, maps: list[R6Map]) -> None:
        """Modify the selected maps of a custom map pool.

        Args:
            name (str): The name of the custom map pool.
            maps (list[R6Map]): The updated list of maps to include in the
                custom map pool.
        """
        pool = self.get_map_pool(name)
        pool.set_maps(maps)

    def serialise(self) -> dict:
        """Convert SettingsEntry instance representation into a dict.

        Returns:
            dict: Dictionary representation of the SettingsEntry instance.
        """
        return {
            "admins": self.__admins,
            "text_channel_id": self.__text_channel_id,
            "map_pools": [pool.serialise() for pool in self.__map_pools],
        }

    @classmethod
    def create_blank(cls) -> "SettingsEntry":
        """Create a unconfigured SettingsEntry instance.

        Returns:
            SettingsEntry: The created SettingsEntry instance.
        """
        return cls(
            {
                "admins": [],
                "text_channel_id": None,
                "map_pools": [],
            }
        )


class CustomMapPool(WrapperBase):
    """Wrapper class that wraps custom map pool data from the database into a
    python object.
    """

    __slots__ = (
        "__owner_id",
        "__name",
        "__maps",
        "__created_timestamp",
        "__modified_timestamp",
    )

    def __init__(self, data: dict):
        self.__owner_id: int = int(data["owner_id"])
        self.__name: str = data["name"]
        self.__maps: list[R6Map] = [R6Map(name) for name in data["maps"]]
        self.__created_timestamp: int = data["created_timestamp"]
        self.__modified_timestamp: int = data["modified_timestamp"]

    def __len__(self) -> int:
        return len(self.__maps)

    def __iter__(self) -> Generator[Any, Any, R6Map | None]:
        yield from self.__maps

    @property
    def owner_id(self) -> int:
        """The user ID of the bot administrator that created the custom map
        pool.
        """
        return self.__owner_id

    @property
    def name(self) -> str:
        """The name of the custom map pool."""
        return self.__name

    @property
    def maps(self) -> list[R6Map]:
        """The list of included maps in the custom map pool."""
        return self.__maps

    @property
    def created_timestamp(self) -> int:
        """The UNIX timestamp at which the custom map pool was created."""
        return self.__created_timestamp

    @property
    def modified_timestamp(self) -> int:
        """The UNIX timestamp at which the custom map pool was last modified."""
        return self.__modified_timestamp

    def set_owner(self, owner_id: int) -> None:
        """Set the owner ID of the custom map pool.

        Args:
            owner_id (int): The user ID of the new owner.
        """
        self.__owner_id = owner_id
        self.update_modified_timestamp()

    def set_name(self, name: str) -> None:
        """Set the name of the custom map pool.

        Args:
            name (str): The new name to use.
        """
        self.__name = name
        self.update_modified_timestamp()

    def set_maps(self, maps: list[R6Map]) -> None:
        """Set the maps to be included in the custom map pool.

        Args:
            maps (list[R6Map]): The new list of maps to use.
        """
        self.__maps = maps
        self.update_modified_timestamp()

    def update_modified_timestamp(self) -> None:
        """Update the modified timestamp to the current UNIX timestamp."""
        self.__modified_timestamp = int(datetime.now().timestamp())

    def serialise(self) -> dict:
        """Convert CustomMapPool instance representation into a dict.

        Returns:
            dict: Dictionary representation of the CustomMapPool instance.
        """
        return {
            "owner_id": self.__owner_id,
            "name": self.__name,
            "maps": self.__maps,
            "created_timestamp": self.__created_timestamp,
            "modified_timestamp": self.__modified_timestamp,
        }

    @classmethod
    def create(cls, owner_id: int, name: str, maps: list[R6Map]) -> "CustomMapPool":
        """Create a CustomMapPool instance with the provided data.

        Args:
            owner_id (int): The user ID of the bot administrator that created
                the custom map pool.
            name (str): The name of the custom map pool.
            maps (list[R6Map]): The list of maps to be included in the custom
                map pool.

        Returns:
            CustomMapPool: The newly created CustomMapPool instance.
        """
        timestamp = int(datetime.now().timestamp())
        return cls(
            {
                "owner_id": owner_id,
                "name": name,
                "maps": maps,
                "created_timestamp": timestamp,
                "modified_timestamp": timestamp,
            }
        )
