from typing import Optional

import discord

__all__ = (
    "AlreadyInQueue",
    "NoListResults",
    "NotInQueue",
    "NotQueueOwner",
    "QueueAlreadyExists",
    "QueueDoesNotExist",
    "QueueLimitReached",
    "QueueIsFull",
    "QueueIsLocked",
    "QueueLockStateError",
    "QueueProgressStateError",
)


class AlreadyInQueue(Exception):
    def __init__(self, user_id: int):
        self.user_id = user_id

    def __str__(self):
        return f"AlreadyInQueue[user_id={self.user_id}]"


class NoListResults(Exception):
    def __init__(
        self, member: Optional[discord.Member] = None, queue_type: Optional[str] = None
    ):
        self.member = member
        self.queue_type = queue_type

    def __str__(self):
        return f"NoListResults[member={self.member}, queue_type={self.queue_type}]"


class NotInQueue(Exception):
    def __init__(self, user_id: int):
        self.user_id = user_id

    def __str__(self):
        return f"NotInQueue[user_id={self.user_id}]"


class NotQueueOwner(Exception):
    def __init__(self, real: int, provided: int):
        self.real_id = real
        self.provided_id = provided

    def __str__(self):
        return f"NotQueueOwner[real_id={self.real_id}, provided_id={self.provided_id}]"


class QueueAlreadyExists(Exception):
    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.msg = f'Queue with name "{queue_name}" already exists'

    def __str__(self):
        return f"QueueAlreadyExists[name={self.queue_name}]"


class QueueDoesNotExist(Exception):
    def __init__(self, queue_name: str):
        self.queue_name = queue_name

    def __str__(self):
        return f"QueueDoesNotExist[queue_name={self.queue_name}]"


class QueueLimitReached(Exception):
    def __init__(self, guild_id: int):
        self.guild_id = guild_id

    def __str__(self):
        return f"QueueLimitReached[guild_id={self.guild_id}]"


class QueueIsFull(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "QueueIsFull"


class QueueIsLocked(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "QueueIsLocked"


class QueueLockStateError(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "QueueLockStateError"


class QueueProgressStateError(Exception):
    def __init__(self):
        pass

    def __str__(self):
        return "QueueProgressStateError"
