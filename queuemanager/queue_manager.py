from datetime import UTC, datetime

import discord

from base import ManagerBase
from exceptions import (
    NoListResults,
    QueueIsFull,
    QueueLimitReached,
    QueueLockStateError,
)

from .enums import MAX_ENQUEUED_PLAYERS, QueueType
from .queue import QueueEntry, QueueWrapper


class QueueManager(ManagerBase):
    """Database manager to manage queue-related data."""

    def __init__(self, queue_loc: str):
        super().__init__(queue_loc, "queues")

    async def load(self):
        """Create the necessary directories and load into memory."""
        await super()._load(name="QueueManager")

    async def get_or_create_wrapper(self) -> QueueWrapper:
        """Get or create the QueueWrapper.

        Returns:
            QueueWrapper: The QueueWrapper instance.
        """
        return await super()._get_or_create_wrapper(cls=QueueWrapper)

    async def can_create_queue(self, *, guild_id: int) -> bool:
        """Check if a queue can be created in the specified guild.

        Args:
            guild_id (int): The ID of the guild to check.

        Returns:
            bool: Whether or not a queue can be created.
        """
        wrapper = await self.get_or_create_wrapper()
        return len(wrapper.get_or_create(guild_id).data.values()) < 20

    async def create_queue(
        self,
        *,
        guild_id: int,
        owner_id: int,
        name: str,
        queue_type: QueueType,
        notify: bool,
    ) -> None:
        """Create a queue.

        Args:
            guild_id (int): The ID of the guild to create the queue in.
            owner_id (int): The user ID of the player that initiated the
            creation of the queue.
            name (str): The name of the queue to be created.
            queue_type (QueueType): The queue type of the queue to be created.
            notify (bool): Whether or not the queue owner will be notified upon
                players joining or leaving the queue.

        Raises:
            QueueLimitReached: The guild has reached its maximum amount of
            simultaneous open queues and a new one cannot be created.
        """
        wrapper = await self.get_or_create_wrapper()

        # Do not allow more than 20 simultaneous open queues at a time
        if len(wrapper.get_or_create(guild_id).data.values()) >= 20:
            raise QueueLimitReached(guild_id)

        queue_entry_data = {
            "owner_id": owner_id,
            "created_timestamp": int(datetime.now(tz=UTC).timestamp()),
            "type": queue_type,
            "players": [],
            "max_players": MAX_ENQUEUED_PLAYERS.get(queue_type),
            "invites": [],
            "locked": False,
            "in_progress": False,
            "notify": notify,
        }
        wrapper.get_or_create(guild_id).create(name.lower(), queue_entry_data)
        await self.write(wrapper)

    async def delete_queue(
        self, guild_id: int, name: str, user_id: int, admin: bool = False
    ) -> None:
        """Delete a queue.

        Args:
            guild_id (int): The ID of the guild to delete the queue in.
            name (str): The name of the queue to be deleted.
            user_id (int): The user ID of the user attempting to perform
                this operation.
            admin (bool, optional): Whether or not the user is a bot
                administrator. Defaults to False.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).delete(name, user_id, admin=admin)
        await self.write(wrapper)

    async def join_user_to_queue(
        self, guild_id: int, user_id: int, name: str
    ) -> QueueEntry:
        """Join a user to a queue.

        Args:
            guild_id (int): The ID of the guild the queue is in.
            user_id (int): The user ID of the player attempting to join
                the queue.
            name (str): The name of the queue.

        Returns:
            QueueEntry: The corresponding entry of the queue the player joined.
        """
        wrapper = await self.get_or_create_wrapper()
        queue = wrapper.get_or_create(guild_id).get(name.lower(), throw=True)
        queue.add_player(user_id)
        await self.write(wrapper)
        return queue

    async def leave_user_from_queue(
        self, guild_id: int, user_id: int, name: str, force: bool = False
    ) -> QueueEntry:
        """Leave a user from a queue.

        Args:
            guild_id (int): The ID of the guild the queue is in.
            user_id (int): The user ID of the player attempting to leave
                the queue.
            name (str): The name of the queue.
            force (bool, optional): Whether or not this action should happen
                regardless of queue lock state. Defaults to False.

        Returns:
            QueueEntry: The corresponding entry of the queue the player left.
        """
        wrapper = await self.get_or_create_wrapper()
        queue = wrapper.get_or_create(guild_id).get(name.lower(), throw=True)
        queue.remove_player(user_id, force)
        await self.write(wrapper)
        return queue

    async def check_can_invite_users_to_queue(
        self, guild_id: int, users: list[discord.User | discord.Member], name: str
    ) -> tuple[list[discord.User], list[discord.User], list[discord.User]]:
        """Check if certain users can be invited to a queue.

        Args:
            guild_id (int): The ID of the guild the queue is in.
            users (list[discord.User | discord.Member]): The users to check.
            name (str): The name of the queue.

        Raises:
            QueueIsFull: The queue is full and cannot accept any more players.

        Returns:
            tuple[list[discord.User], list[discord.User]]: Users that can be
                invited and users that cannot be invited.
        """
        wrapper = await self.get_or_create_wrapper()
        entry = wrapper.get_or_create(guild_id).get(name.lower(), throw=True)
        if entry.full:
            raise QueueIsFull

        invitable, non_invitable, bot = [], [], []
        for user in users:
            _list = (
                bot
                if user.bot
                else non_invitable
                if user.id in entry.players or user.id in entry.invites
                else invitable
            )
            _list.append(user)
        return invitable, non_invitable, bot

    async def add_invite(self, guild_id: int, user_id: int, name: str) -> None:
        """Add a user ID to the invites list for a queue.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The ID of the user.
            name (str): The name of the queue.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).get(name.lower(), throw=True).add_invite(
            user_id
        )
        await self.write(wrapper)

    async def remove_invite(self, guild_id: int, user_id: int, name: str) -> None:
        """Remove a user ID to the invites list for a queue.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The ID of the user.
            name (str): The name of the queue.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).get(name.lower(), throw=True).remove_invite(
            user_id
        )
        await self.write(wrapper)

    async def set_queue_lock_state(
        self, guild_id: int, user_id: int, name: str, state: bool, admin: bool = False
    ) -> None:
        """Set the queue lock state.

        Args:
            guild_id (int): The ID of the guild the queue is in.
            user_id (int): The user ID of the user attempting to perform
            this operation.
            name (str): The name of the queue.
            state (bool): The desired queue lock state.
            admin (bool, optional): Whether or not the user is a bot
            administrator. Defaults to False.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).get(name.lower(), throw=True).set_lock(
            user_id, state, admin=admin
        )
        await self.write(wrapper)

    async def set_progress_state(self, guild_id: int, name: str, state: bool) -> None:
        """Set the queue progress state.

        Args:
            guild_id (int): The ID of the guild the queue is in.
            name (str): The name of the queue.
            state (bool): The desired queue progress state.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).get(name.lower(), throw=True).set_progress(
            state
        )
        await self.write(wrapper)

    async def set_notify_state(self, guild_id: int, name: str, state: bool) -> None:
        """Set the queue's notify state.

        Args:
            guild_id (int): The ID of the guild the queue is in.
            name (str): The name of the queue.
            state (bool): The desired queue notify state.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).get(name.lower(), throw=True).set_notify(state)
        await self.write(wrapper)

    async def get_queue(self, guild_id: int, name: str) -> QueueEntry | None:
        """Get an individual queue entry matching the specified name.

        Args:
            guild_id (int): The ID of the guild to search.
            name (str): The name of the queue.

        Returns:
            QueueEntry | None: A queue entry, if found.
        """
        wrapper = await self.get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).get(name)

    async def get_all_queues(self, guild_id: int) -> dict[str, QueueEntry]:
        """Get a dictionary containing all queues in a guild.

        Args:
            guild_id (int): The ID of the guild to search.

        Returns:
            dict[str, QueueEntry]: A dictionary containing all queues in the
                specified guild.
        """
        wrapper = await self.get_or_create_wrapper()
        return wrapper.get_or_create(guild_id).data

    async def get_queues_owned_by(
        self, guild_id: int, owner_id: int, admin: bool = False
    ) -> dict[str, QueueEntry]:
        """Get all queues in the guild owned by the user.

        Args:
            guild_id (int): The ID of the guild to search.
            owner_id (int): The user ID of the user.
            admin (bool, optional): Whether or not the user is a bot
            administrator. Defaults to False.

        Returns:
            dict[str, QueueEntry]: A dictionary containing all queues in the
            specified guild which the user owns or can manage.
        """
        queues = await self.get_all_queues(guild_id)
        return {
            name: entry
            for name, entry in queues.items()
            if admin or entry.owner_id == owner_id
        }

    async def list_queues(
        self,
        guild_id: int,
        member: discord.Member | discord.User | None = None,
        queue_type: QueueType | None = None,
    ) -> dict[str, QueueEntry]:
        """List all queues in the guild that match the provided filters.

        Args:
            guild_id (int): The ID of the guild to search.
            member (Optional[discord.Member  |  discord.User], optional): A
                user to filter for queue ownership. Defaults to None.
            queue_type (Optional[QueueType], optional): A queue type to filter.
                Defaults to None.

        Raises:
            NoListResults: No queues matched the provided filters.

        Returns:
            dict[str, QueueEntry]: A dictionary containing all queues that
                matched the provided filters.
        """
        wrapper = await self.get_or_create_wrapper()
        results = wrapper.get_or_create(guild_id).filter(
            member=member, queue_type=queue_type
        )
        if not results:
            raise NoListResults(member=member, queue_type=queue_type)

        return results

    async def start_match(
        self, guild_id: int, owner_id: int, name: str, admin: bool = False
    ) -> QueueEntry:
        """Start a match from a queue.

        Args:
            guild_id (int): The ID of the guild the queue is in.
            owner_id (int): The user ID of the user that is the queue owner.
            name (str): The name of the queue.
            admin (bool, optional): Whether or not the user is a bot
                administrator. Defaults to False.

        Returns:
            QueueEntry: The QueueEntry corresponding to the queue that had a
                match started.
        """
        try:
            await self.set_queue_lock_state(guild_id, owner_id, name, True, admin=admin)
        except QueueLockStateError:
            pass

        await self.set_progress_state(guild_id, name, True)

        wrapper = await self.get_or_create_wrapper()
        entry = wrapper.get(guild_id, throw=True).get(name, throw=True)
        if len(entry.players) == 2:
            entry.type = QueueType.R6_1V1

        return entry
