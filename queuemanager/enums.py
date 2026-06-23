from enum import StrEnum

__all__ = (
    "CaptSelect",
    "QueueType",
    "ALL_R6_QUEUE_TYPES",
    "ALL_CAPT_SELECT_MODES",
)


class QueueType(StrEnum):
    R6_5V5 = "Rainbow Six Siege - 5v5"
    R6_1V1 = "Rainbow Six Siege - 1v1"


class CaptSelect(StrEnum):
    RANDOM = "random"
    RATING = "rating"
    MANUAL = "manual"


ALL_R6_QUEUE_TYPES = [
    QueueType.R6_5V5,
    QueueType.R6_1V1,
]


ALL_CAPT_SELECT_MODES = [
    CaptSelect.RATING,
    CaptSelect.RANDOM,
    CaptSelect.MANUAL,
]
