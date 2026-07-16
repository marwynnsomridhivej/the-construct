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
    """Exception raised when attempting to join a user to a queue
    they are already in.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id

    def __str__(self):
        return f"AlreadyInQueue[user_id={self.user_id}]"


class NoListResults(Exception):
    """Exception raised when no queue list results are found with
    the specified member and/or queue type filters.
    """

    def __init__(
        self,
        member: Optional[discord.Member | discord.User] = None,
        queue_type: Optional[str] = None,
    ):
        self.member = member
        self.queue_type = queue_type

    def __str__(self):
        return f"NoListResults[member={self.member}, queue_type={self.queue_type}]"


class NotInQueue(Exception):
    """Exception raised when attempting to perform an operation in
    a given queue on a user that is not a member of said queue.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id

    def __str__(self):
        return f"NotInQueue[user_id={self.user_id}]"


class NotQueueOwner(Exception):
    """Exception raised when attempting to perform a queue operation
    that is reserved for the queue owner or bot administrator while
    having neither of those permissions.
    """

    def __init__(self, real: int, provided: int):
        self.real_id = real
        self.provided_id = provided

    def __str__(self):
        return f"NotQueueOwner[real_id={self.real_id}, provided_id={self.provided_id}]"


class QueueAlreadyExists(Exception):
    """Exception raised when attempting to create a queue with the
    same name as one that currently exists.
    """

    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.msg = f'Queue with name "{queue_name}" already exists'

    def __str__(self):
        return f"QueueAlreadyExists[name={self.queue_name}]"


class QueueDoesNotExist(Exception):
    """Exception raised when attempting to perform queue operations
    on a queue that does not exist.
    """

    def __init__(self, queue_name: str):
        self.queue_name = queue_name

    def __str__(self):
        return f"QueueDoesNotExist[queue_name={self.queue_name}]"


class QueueLimitReached(Exception):
    """Exception raised when attempting to create a new queue when
    the server has reached the maximum amount of simultaneous active
    queues.
    """

    def __init__(self, guild_id: int):
        self.guild_id = guild_id

    def __str__(self):
        return f"QueueLimitReached[guild_id={self.guild_id}]"


class QueueIsFull(Exception):
    """Exception raised when a user attempts to join a queue
    that has reached its maximum occupancy.
    """

    def __init__(self):
        pass

    def __str__(self):
        return "QueueIsFull"


class QueueIsLocked(Exception):
    """Exception raised when attempting to perform a queue operation on
    a queue that is currently locked.
    """

    def __init__(self):
        pass

    def __str__(self):
        return "QueueIsLocked"


class QueueLockStateError(Exception):
    """Exception raised when attempting to change a queue's lock
    state to the state it is already in.
    """

    def __init__(self):
        pass

    def __str__(self):
        return "QueueLockStateError"


class QueueProgressStateError(Exception):
    """Exception raised when attempting to change a queue's in
    progress state to the state it is already in.
    """

    def __init__(self):
        pass

    def __str__(self):
        return "QueueProgressStateError"
