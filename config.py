import json
import os
from typing import Set


class Config(object):
    __slots__ = (
        "__token",
        "owner_ids",
        "nexus_guild_id",
        "data_dir",
        "log_dir",
        "command_prefix",
        "cogs",
    )

    def __init__(self):
        self.load()

    def serialise(self) -> dict:
        return {
            "token": self.__token,
            "owner_ids": self.owner_ids,
            "nexus_guild_id": self.nexus_guild_id,
            "data_dir": self.data_dir,
            "log_dir": self.log_dir,
            "command_prefix": self.command_prefix,
        }

    def load(self) -> None:
        with open("./config.json", "r") as file:
            data = json.loads(file.read())
        self.__token = data["token"]
        self.owner_ids: Set[int] = set(data["owner_ids"])
        self.nexus_guild_id = data["nexus_guild_id"]
        self.data_dir = data["data_dir"]
        self.log_dir = data["log_dir"]
        self.command_prefix = data["command_prefix"]

        # Dynamically find cogs based on filename criteria
        self.cogs = [
            f"cogs.{_dir[:-3]}"
            for _dir in os.listdir("./cogs")
            if _dir.endswith("_cog.py")
        ]

        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)

        if not os.path.exists(self.log_dir):
            os.mkdir(self.log_dir)

    def save(self) -> None:
        with open("./config.json", "w") as file:
            file.write(json.dumps(self.serialise()))

    @property
    def token(self) -> str:
        return self.__token
