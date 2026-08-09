from __future__ import annotations

import os
import secrets
from collections.abc import Callable, Coroutine
from string import capwords
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
    "SYSTEM_RANDOM",
    # Typehints
    "CoroType",
    "EventHandlerType",
    # Functions
    "ephemeral",
    "titlecase",
)


# Constants
ICON = "https://img.icons8.com/ios_filled/1200/rainbow-six-siege.jpg"

SYSTEM_RANDOM = secrets.SystemRandom(os.urandom(256))


# Util functions
def ephemeral(*, seconds: int = 5) -> dict:
    return {
        "ephemeral": True,
        "delete_after": seconds,
    }


def titlecase(input: str) -> str:
    return capwords(input, " ")


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
