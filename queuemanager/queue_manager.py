from datetime import datetime
from typing import Dict, Optional

import discord

from base import ManagerBase
from exceptions import *

from .enums import QueueType
from .queue import QueueEntry, QueueWrapper

MAX_PLAYERS = {
    QueueType.R6_5V5: 10,
    QueueType.R6_1V1: 2,
}


class QueueManager(ManagerBase):
    def __init__(self, queue_loc: str):
        super().__init__(queue_loc, "queues")

    async def load(self):
        await super().load(name="QueueManager")

    async def _get_or_create_wrapper(self) -> QueueWrapper:
        return await super()._get_or_create_wrapper(cls=QueueWrapper)

    async def create_queue(self, *, guild_id: int, owner_id: int, name: str, queue_type: QueueType) -> None:
        # Do not allow for name to be longer than 100 characters (discord.SelectOption limit)
        if len(name) > 100:
            raise ValueError(name)

        wrapper = await self._get_or_create_wrapper()

        # Do not allow more than 20 simultaneous open queues at a time
        if len(wrapper.get_or_create(guild_id).data.values()) >= 20:
            raise QueueLimitReached

        queue_entry_data = {
            "owner_id":     owner_id,
            "created_timestamp": int(datetime.now().timestamp()),
            "type":         queue_type,
            "players":      [],
            "max_players":  MAX_PLAYERS.get(queue_type),
            "locked": False,
            "in_progress": False,
        }
        wrapper.get_or_create(guild_id).create(name.lower(), queue_entry_data)
        await self.write(wrapper)

    async def delete_queue(self, guild_id: int, name: str, user_id: int) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id).delete(name, user_id)
        await self.write(wrapper)

    async def join_user_to_queue(self, guild_id: int, user_id: int, name: str) -> QueueEntry:
        wrapper = await self._get_or_create_wrapper()
        q = wrapper.get_or_create(guild_id).get(name.lower(), throw=True)
        q.add_player(user_id)
        await self.write(wrapper)
        return q

    async def leave_user_from_queue(self, guild_id: int, user_id: int, name: str, force: bool = False) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id)\
            .get(name.lower(), throw=True)\
            .remove_player(user_id, force)
        await self.write(wrapper)

    async def set_queue_lock_state(self, guild_id: int, user_id: int, name: str, state: bool, admin: bool = False) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id)\
            .get(name.lower(), throw=True)\
            .set_lock(user_id, state, admin=admin)
        await self.write(wrapper)

    async def set_progress_state(self, guild_id: int, name: str, state: bool) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id)\
            .get(name.lower(), throw=True)\
            .set_progress(state)
        await self.write(wrapper)

    async def get_all_queues(self, guild_id: int) -> Dict[str, QueueEntry]:
        wrapper = await self._get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).data

    async def get_queues_owned_by(self, guild_id: int, owner_id: int, admin: bool = False) -> Dict[str, QueueEntry]:
        queues = await self.get_all_queues(guild_id)
        return {name: entry for name, entry in queues.items() if admin or entry.owner_id == owner_id}

    async def list_queues(self, guild_id: int, member: Optional[discord.Member] = None, queue_type: Optional[QueueType] = None) -> Dict[str, QueueEntry]:
        wrapper = await self._get_or_create_wrapper()
        results = wrapper.get_or_create(guild_id).filter(
            member=member,
            queue_type=queue_type
        )
        if not results:
            raise NoListResults(member=member, queue_type=queue_type)

        return results

    async def start_match(self, guild_id: int, owner_id: int, name: str, admin: bool = False) -> QueueEntry:
        try:
            await self.set_queue_lock_state(guild_id, owner_id, name, True, admin=admin)
        except QueueLockStateError:
            pass

        await self.set_progress_state(guild_id, name, True)

        wrapper = await self._get_or_create_wrapper()
        entry = wrapper.get(guild_id, throw=True).get(name, throw=True)
        if len(entry.players) == 2:
            entry.type = QueueType.R6_1V1

        return entry
