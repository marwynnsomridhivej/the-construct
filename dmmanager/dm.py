from typing import Dict, Union

from base import WrapperBase


class DMWrapper(WrapperBase):
    __slots__ = ("data",)

    def __init__(self, data: Dict[str, int]):
        self.data = data

    @staticmethod
    def _key(guild_id: int, user_id: int) -> str:
        return f"{guild_id}_{user_id}"

    def get(self, guild_id: int, user_id: int) -> Union[int, None]:
        return self.data.get(self._key(guild_id, user_id))

    def create(self, guild_id: int, user_id: int, message_id: int) -> None:
        self.data[self._key(guild_id, user_id)] = message_id

    def delete(self, guild_id: int, user_id: int) -> int:
        return self.data.pop(self._key(guild_id, user_id))

    def serialise(self) -> dict:
        return self.data
