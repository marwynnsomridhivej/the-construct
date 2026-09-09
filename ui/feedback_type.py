from enum import StrEnum

__all__ = (
    "FEEDBACK_TYPES",
    "FeedbackType",
)


class FeedbackType(StrEnum):
    BUG = "bug"
    SUGGESTION = "suggestion"


FEEDBACK_TYPES = [
    FeedbackType.BUG,
    FeedbackType.SUGGESTION,
]
