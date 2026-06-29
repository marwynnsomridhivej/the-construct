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
    __slots__ = ("__data",)

    def __init__(self, data: dict):
        self.__data: dict[int, SettingsEntry] = {
            int(guild_id): SettingsEntry.parse(entry)
            for guild_id, entry in data.items()
        }

    def get(self, guild_id: int, throw: bool = False) -> "SettingsEntry | None":
        entry = self.__data.get(guild_id)
        if entry is None and throw:
            raise InvalidGuildID(guild_id)
        return entry

    def get_or_create(self, guild_id: int) -> "SettingsEntry":
        entry = self.get(guild_id)
        if entry is None:
            entry = SettingsEntry.create_blank()
            self.__data[guild_id] = entry
        return entry

    @property
    def data(self) -> dict[int, "SettingsEntry"]:
        return self.__data

    def serialise(self) -> dict:
        return {guild_id: entry.serialise() for guild_id, entry in self.__data.items()}


class SettingsEntry(WrapperBase):
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
        return self.__admins

    @property
    def text_channel_id(self) -> int | None:
        return self.__text_channel_id

    @property
    def map_pools(self) -> list["CustomMapPool"]:
        return self.__map_pools

    def set_admins(self, user_ids: list[int]) -> None:
        self.__admins = user_ids

    def bind_text_channel_id(self, _id: int) -> None:
        self.__text_channel_id = _id

    def create_map_pool(
        self, owner_id: int, name: str, maps: list[R6Map] = []
    ) -> "CustomMapPool":
        name_taken = any([pool.name == name for pool in self.__map_pools])
        if name_taken:
            raise MapPoolAlreadyExists(name)
        pool = CustomMapPool.create(owner_id, name, maps)
        self.__map_pools.append(pool)
        return pool

    def get_map_pool(self, name: str) -> "CustomMapPool":
        pool = discord.utils.find(lambda p: p.name == name, self.__map_pools)
        if pool is None:
            raise MapPoolNotFound(name)
        return pool

    def delete_map_pool(self, name: str) -> None:
        pool = self.get_map_pool(name)
        self.__map_pools.remove(pool)

    def name_map_pool(self, old_name: str, new_name: str) -> None:
        pool = self.get_map_pool(old_name)
        try:
            self.get_map_pool(new_name)
        except MapPoolNotFound:
            pool.set_name(new_name)
        else:
            raise MapPoolAlreadyExists(new_name)

    def modify_map_pool_maps(self, name: str, maps: list[R6Map]) -> None:
        pool = self.get_map_pool(name)
        pool.set_maps(maps)

    def serialise(self) -> dict:
        return {
            "admins": self.__admins,
            "text_channel_id": self.__text_channel_id,
            "map_pools": [pool.serialise() for pool in self.__map_pools],
        }

    @classmethod
    def create_blank(cls) -> "SettingsEntry":
        return cls(
            {
                "admins": [],
                "text_channel_id": None,
                "map_pools": [],
            }
        )


class CustomMapPool(WrapperBase):
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
        return self.__owner_id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def maps(self) -> list[R6Map]:
        return self.__maps

    @property
    def created_timestamp(self) -> int:
        return self.__created_timestamp

    @property
    def modified_timestamp(self) -> int:
        return self.__modified_timestamp

    def set_owner(self, owner_id: int) -> None:
        self.__owner_id = owner_id
        self.update_modified_timestamp()

    def set_name(self, name: str) -> None:
        self.__name = name
        self.update_modified_timestamp()

    def set_maps(self, maps: list[R6Map]) -> None:
        self.__maps = maps
        self.update_modified_timestamp()

    def update_modified_timestamp(self) -> None:
        self.__modified_timestamp = int(datetime.now().timestamp())

    def serialise(self) -> dict:
        return {
            "owner_id": self.__owner_id,
            "name": self.__name,
            "maps": self.__maps,
            "created_timestamp": self.__created_timestamp,
            "modified_timestamp": self.__modified_timestamp,
        }

    @classmethod
    def create(cls, owner_id: int, name: str, maps: list[R6Map]) -> "CustomMapPool":
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
