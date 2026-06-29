from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

import discord

if TYPE_CHECKING:
    from event import (
        DMDeletePayload,
        MatchFinalisedPayload,
        MatchPayload,
        PlayerStatsResetPayload,
        PrematchDMPayload,
        QueueFilledPayload,
        SeasonEndPayload,
        VCResetPayload,
    )

__all__ = (
    # Constants
    "ICON",
    # Functions
    "ephemeral",
    # Typehints
    "CoroType",
    "EventHandlerType",
)


# Constants
ICON = "https://img.icons8.com/ios_filled/1200/rainbow-six-siege.jpg"


# Util functions
def ephemeral(*, seconds: int = 5) -> dict:
    return {
        "ephemeral": True,
        "delete_after": seconds,
    }


# Typehints
type CoroType = Coroutine[Any, Any, None]
type EventHandlerType = (
    Callable[[discord.Guild], CoroType]
    | Callable[[discord.RawMemberRemoveEvent], CoroType]
    | Callable[[discord.RawMessageDeleteEvent], CoroType]
    | Callable[[DMDeletePayload], CoroType]
    | Callable[[int], CoroType]
    | Callable[[MatchFinalisedPayload], CoroType]
    | Callable[[MatchPayload], CoroType]
    | Callable[[PlayerStatsResetPayload], CoroType]
    | Callable[[PrematchDMPayload], CoroType]
    | Callable[[QueueFilledPayload], CoroType]
    | Callable[[SeasonEndPayload], CoroType]
    | Callable[[VCResetPayload], CoroType]
)
