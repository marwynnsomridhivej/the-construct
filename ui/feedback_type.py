from enum import StrEnum

__all__ = (
    "FeedbackType",
    "FEEDBACK_TYPES",
)


class FeedbackType(StrEnum):
    BUG = "bug"
    SUGGESTION = "suggestion"


FEEDBACK_TYPES = [
    FeedbackType.BUG,
    FeedbackType.SUGGESTION,
]
