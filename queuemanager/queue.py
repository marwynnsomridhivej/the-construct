from typing import Literal, overload

import discord

from base import WrapperBase
from exceptions import (
    AlreadyInQueue,
    InvalidGuildID,
    NotInQueue,
    NotQueueOwner,
    QueueAlreadyExists,
    QueueDoesNotExist,
    QueueIsFull,
    QueueIsLocked,
    QueueLockStateError,
    QueueProgressStateError,
)

from .enums import QueueType

__all__ = (
    "QueueWrapper",
    "QueueGuildContainer",
    "QueueEntry",
    "QueueOperationResult",
)


class QueueWrapper(WrapperBase):
    """Wrapper class that wraps queue related data from the database into
    a python object.
    """

    __slots__ = ("__data",)

    def __init__(self, data: dict):
        self.__data: dict[int, QueueGuildContainer] = {
            int(guild_id): QueueGuildContainer.parse(queues)
            for guild_id, queues in data.items()
        }

    @overload
    def get(self, guild_id: int, throw: Literal[True]) -> "QueueGuildContainer": ...

    @overload
    def get(
        self, guild_id: int, throw: Literal[False]
    ) -> "QueueGuildContainer | None": ...

    @overload
    def get(self, guild_id: int) -> "QueueGuildContainer | None": ...

    def get(self, guild_id: int, throw: bool = False) -> "QueueGuildContainer | None":
        """Get a QueueGuildContainer (QGC) of the specified guild.

        Args:
            guild_id (int): The guild ID of the guild.
            throw (bool): Whether or not to throw an exception if a QGC instance
                is not found.

        Raises:
            InvalidGuildID: No QGC instance exists for the specified guild.

        Returns:
            QueueGuildContainer | None: The QGC instance of the specified guild.
        """
        qgc = self.__data.get(guild_id)
        if qgc is None and throw:
            raise InvalidGuildID(guild_id)
        return qgc

    def get_or_create(self, guild_id: int) -> "QueueGuildContainer":
        """Get or create a QueueGuildContainer (QGC) for the specified guild.

        Args:
            guild_id (int): The ID of the guild.

        Returns:
            QueueGuildContainer: An existing QGC instance or a newly created blank
                instance.
        """
        qgc = self.get(guild_id)
        if qgc is None:
            qgc = QueueGuildContainer({})
            self.__data[guild_id] = qgc
        return qgc

    @property
    def data(self) -> dict[int, "QueueGuildContainer"]:
        """Obtain python dictionary data.

        Returns:
            dict[int, QueueGuildContainer]: The underlying python dict object.
        """
        return self.__data

    def serialise(self) -> dict:
        """Convert Queue instance representation into a dict

        Returns:
            dict: Dictionary representation of the Queue instance
        """
        return {guild_id: qgc.serialise() for guild_id, qgc in self.__data.items()}


class QueueGuildContainer(WrapperBase):
    """Wrapper class that wraps guild specific queue data from the database into
    a python object.
    """

    __slots__ = ("__data",)

    def __init__(self, data: dict):
        self.__data = {name: QueueEntry.parse(entry) for name, entry in data.items()}

    @overload
    def get(self, name: str, throw: Literal[True]) -> "QueueEntry": ...

    @overload
    def get(self, name: str, throw: Literal[False]) -> "QueueEntry | None": ...

    @overload
    def get(self, name: str) -> "QueueEntry | None": ...

    def get(self, name: str, throw: bool = False) -> "QueueEntry | None":
        """Get a QueueEntry with the specified name.

        Args:
            name (str): The name of the desired QueueEntry instance
            throw (bool): Whether or not to throw an exception if a QueueEntry
                instance is not found.

        Raises:
            QueueDoesNotExist: No QueueEntry instance exists with the specified
                name.

        Returns:
            QueueEntry | None: The QueueEntry instance with the specified name.
        """
        data = self.__data.get(name)
        if data is None and throw:
            raise QueueDoesNotExist(name)
        return data

    def create(self, name: str, data: dict) -> None:
        """Create a QueueEntry with specified name and data.

        Args:
            name (str): The name of the queue.
            data (dict): The attributes of the queue.

        Raises:
            QueueAlreadyExists: Exception thrown when name is already in use.
        """
        if self.__data.get(name) is not None:
            raise QueueAlreadyExists(name)
        self.__data[name] = QueueEntry.parse(data)

    def delete(self, name: str, user_id: int, admin: bool = False) -> "QueueEntry":
        """Delete a QueueEntry with the specified name.

        Args:
            name (str): The name of the queue
            user_id (int): The ID of the user that is attempting to delete the
                queue.
            admin (bool): Whether or not the user is a bot administrator.
                Defaults to False.

        Raises:
            QueueDoesNotExist: No QueueEntry instance exists with the specified
                name.
            NotQueueOwner: The user is not the owner of the queue.

        Returns:
            QueueEntry: QueueEntry instance that has been deleted.
        """
        queue_entry = self.__data.get(name)
        if queue_entry is None:
            raise QueueDoesNotExist(name)

        if not admin and queue_entry.owner_id != user_id:
            raise NotQueueOwner(real=queue_entry.owner_id, provided=user_id)

        return self.__data.pop(name)

    def filter(
        self,
        *,
        member: discord.Member | discord.User | None,
        queue_type: QueueType | None = None,
    ) -> dict[str, "QueueEntry"]:
        """Filter all stored QueueEntry by user presence or queue type.

        Args:
            member (discord.Member | discord.User | None): The ID of the user to
                filter by.
            queue_type (QueueType | None): The QueueType to filter by.

        Returns:
            dict[str, QueueEntry]: dict containing queue name and QueueEntry
                instance.
        """
        user_id = member.id if member is not None else None
        return {
            name: entry
            for name, entry in self.__data.items()
            if (user_id is None or user_id in entry.players)
            and (queue_type is None or queue_type == entry.type)
        }

    @property
    def data(self) -> dict[str, "QueueEntry"]:
        """Obtain python dictionary data.

        Returns:
            dict[str, QueueEntry]: The underlying python dict object.
        """
        return self.__data

    def serialise(self) -> dict:
        """Convert QueueGuildContainer (QGC) instance representation into a dict

        Returns:
            dict: Dictionary representation of the QGC instance
        """
        return {name: entry.serialise() for name, entry in self.__data.items()}


class QueueEntry(WrapperBase):
    """Wrapper class that wraps queue entry data from the database into
    a python object.
    """

    __slots__ = (
        "owner_id",
        "created_timestamp",
        "type",
        "players",
        "max_players",
        "locked",
        "in_progress",
    )

    def __init__(self, data: dict):
        self.owner_id: int = data["owner_id"]
        self.created_timestamp: int = data["created_timestamp"]
        self.type: QueueType = data["type"]
        self.players: list[int] = data["players"]
        self.max_players: int = data["max_players"]
        self.locked: bool = data["locked"]
        self.in_progress: bool = data["in_progress"]

    def add_player(self, user_id: int) -> None:
        """Add a user ID to the player list.

        Args:
            user_id (int): The ID of the user to add.

        Raises:
            AlreadyInQueue: The user is already in this queue.
            QueueIsFull: The queue is full and cannot accept any new users.
            QueueIsLocked: The queue is locked and cannot be modified.
        """
        if self.locked:
            raise QueueIsLocked

        if user_id in self.players:
            raise AlreadyInQueue(user_id)

        if len(self.players) >= self.max_players:
            raise QueueIsFull

        self.players.append(user_id)

    def remove_player(self, user_id: int, force: bool) -> None:
        """Remove a user ID from the player list.

        Args:
            user_id (int): The ID of the user to remove.
            force (bool): Whether or not to force removal so long as the queue
                is not in progress.

        Raises:
            QueueProgressStateError: There is currently an active match with
                this queue and cannot be modified.
            QueueIsLocked: The queue is locked and cannot be modified.
            NotInQueue: The user is not in this queue.
        """
        if self.locked:
            if force:
                if self.in_progress:
                    raise QueueProgressStateError
            else:
                raise QueueIsLocked

        if user_id not in self.players:
            raise NotInQueue(user_id)

        self.players.remove(user_id)

    def set_lock(self, user_id: int, state: bool, admin: bool = False) -> None:
        """Set the queue's lock state.

        Args:
            user_id (int): The ID of the user attempting to modify this queue.
            state (bool): The state to set the queue's lock.
            admin (bool, optional): Whether or not the user is a bot
                administrator. Defaults to False.

        Raises:
            QueueProgressStateError: The queue is currently in progress and
                cannot be modified.
            NotQueueOwner: The user is not the owner of the queue.
            QueueLockStateError: The specified state does not change the queue's
                lock state.
        """
        if self.in_progress:
            raise QueueProgressStateError

        if user_id != self.owner_id and not admin:
            raise NotQueueOwner(real=self.owner_id, provided=user_id)

        if self.locked == state:
            raise QueueLockStateError

        self.locked = state

    def set_progress(self, state: bool) -> None:
        """Set the queue's in_progress flag.

        Args:
            state (bool): The value to set the queue's in_progress flag.

        Raises:
            QueueProgressStateError: The specified state does not change the
                queue's in_progress flag.
        """
        if self.in_progress == state:
            raise QueueProgressStateError

        self.in_progress = state

    @property
    def full(self) -> bool:
        """Check if the queue has reached maximum capacity.

        Returns:
            bool: Whether or not the queue is full.
        """
        return len(self.players) >= self.max_players

    def serialise(self) -> dict:
        """Convert QueueEntry instance representation into a dict.

        Returns:
            dict: Dictionary representation of the QueueEntry instance.
        """
        return {
            "owner_id": self.owner_id,
            "created_timestamp": self.created_timestamp,
            "type": self.type,
            "players": self.players,
            "max_players": self.max_players,
            "locked": self.locked,
            "in_progress": self.in_progress,
        }


class QueueOperationResult(WrapperBase):
    """Wrapper class that wraps queue operation result data into a
    python object.
    """

    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.entry: QueueEntry | None = data.get("entry")
        self.success: bool = data["success"]
        self.msg: str | None = data["msg"]

    def serialise(self) -> dict:
        """Convert QueueOperationResult instance representation into a dict.

        Returns:
            dict: Dictionary representation of the QueueOperationResult
                instance.
        """
        return {
            "name": self.name,
            "entry": self.entry,
            "success": self.success,
            "msg": self.msg,
        }
