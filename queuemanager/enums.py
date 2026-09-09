from enum import StrEnum

__all__ = (
    "ALL_CAPT_SELECT_MODES",
    "ALL_R6_QUEUE_TYPES",
    "MAX_ENQUEUED_PLAYERS",
    "CaptSelect",
    "QueueNotifyAction",
    "QueueType",
)


class QueueType(StrEnum):
    """Standard text representation of Rainbow Six Siege queue types."""

    R6_5V5 = "Rainbow Six Siege - 5v5"
    R6_1V1 = "Rainbow Six Siege - 1v1"


class QueueNotifyAction(StrEnum):
    """Standard text representation of notifiable queue actions."""

    JOIN = "joined"
    LEAVE = "left"


class CaptSelect(StrEnum):
    """Standard text representation of Rainbow Six Siege captain
    selection modes.
    """

    RANDOM = "random"
    RATING = "rating"
    MANUAL = "manual"


ALL_R6_QUEUE_TYPES = [
    QueueType.R6_5V5,
    QueueType.R6_1V1,
]
"""All Rainbow Six Siege queue types"""


ALL_CAPT_SELECT_MODES = [
    CaptSelect.RATING,
    CaptSelect.RANDOM,
    CaptSelect.MANUAL,
]
"""All Rainbow Six Siege captain selection modes."""


MAX_ENQUEUED_PLAYERS = {
    QueueType.R6_5V5: 10,
    QueueType.R6_1V1: 2,
}
"""The maximum number of players in a queue for a given queue type."""
