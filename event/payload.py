from typing import Dict, List, Tuple, Union

import discord

from base import WrapperBase
from matchmanager import MatchEntry, MatchTeam
from queuemanager import QueueEntry, QueueType
from settingsmanager import CustomMapPool
from statsmanager import StatsPlayer, StatsSeason

__all__ = (
    # Queue
    "QueueFilledPayload",
    # R6 Match
    "PrematchPayload",
    "PrematchDMPayload",
    "AutoDraftPayload",
    "DMDeletePayload",
    "VCResetPayload",
    "MatchFinalisedPayload",
    # Seasons
    "SeasonEndPayload",
    # Stats
    "PlayerStatsResetPayload",
)


class QueueFilledPayload(WrapperBase):
    slots = (
        "__guild_id",
        "__name",
        "__entry",
    )

    def __init__(self, data: dict):
        self.__guild_id: int = data["guild_id"]
        self.__name: str = data["name"]
        self.__entry: QueueEntry = data["entry"]

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def entry(self) -> QueueEntry:
        return self.__entry

    def serialise(self) -> dict:
        return {
            "guild_id": self.__guild_id,
            "name": self.__name,
            "entry": self.__entry,
        }


class PrematchPayload(WrapperBase):
    __slots__ = (
        "__guild_id",
        "__match_name",
        "__voice_channel_id",
        "__text_channel_id",
        "__map_pool",
        "__auto_draft",
        "__captains",
        "__queue_entry",
        "__match_entry",
    )

    def __init__(self, data: dict):
        self.__guild_id: int = data["guild_id"]
        self.__match_name: str = data["match_name"]
        self.__voice_channel_id: int = data["voice_channel_id"]
        self.__text_channel_id: int = data["text_channel_id"]
        self.__map_pool: CustomMapPool = CustomMapPool.parse(data["map_pool"])
        self.__auto_draft: bool = data["auto_draft"]
        self.__captains: Tuple[int, int] = data["captains"]
        self.__queue_entry: QueueEntry = QueueEntry(data["queue_entry"])
        self.__match_entry: Union[MatchEntry, None] = (
            MatchEntry(data.get("match_entry")) if data.get("match_entry") else None
        )

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def match_name(self) -> str:
        return self.__match_name

    @property
    def voice_channel_id(self) -> int:
        return self.__voice_channel_id

    @property
    def text_channel_id(self) -> int:
        return self.__text_channel_id

    @property
    def map_pool(self) -> CustomMapPool:
        return self.__map_pool

    @property
    def auto_draft(self) -> bool:
        return self.__auto_draft

    @property
    def captains(self) -> Tuple[int, int]:
        return self.__captains

    @property
    def queue_entry(self) -> QueueEntry:
        return self.__queue_entry

    @property
    def match_entry(self) -> Union[MatchEntry, None]:
        return self.__match_entry

    def switch_to_thread_channel(self, thread_id: int) -> None:
        self.__text_channel_id = thread_id

    def attach_match_entry(self, match_entry: MatchEntry) -> None:
        self.__match_entry = match_entry

    def set_auto_draft_captains(self, payload: "AutoDraftPayload") -> None:
        self.__captains = (payload.team_a_captain, payload.team_b_captain)

    def serialise(self) -> dict:
        return {
            "guild_id": self.__guild_id,
            "match_name": self.__match_name,
            "voice_channel_id": self.__voice_channel_id,
            "text_channel_id": self.__text_channel_id,
            "map_pool": self.__map_pool.serialise(),
            "auto_draft": self.__auto_draft,
            "captains": self.__captains,
            "queue_entry": self.__queue_entry.serialise(),
            "match_entry": getattr(self.__match_entry, "serialise", lambda: None)(),
        }


class PrematchDMPayload(PrematchPayload):
    __slots__ = ("__message",)

    def __init__(self, data: dict):
        super().__init__(data)
        self.__message: discord.Message = data["message"]

    @property
    def message(self) -> discord.Message:
        return self.__message

    def serialise(self):
        data = super().serialise()
        data["message"] = self.__message
        return data

    @classmethod
    def from_prematch_payload(
        cls, payload: PrematchPayload, message: discord.Message
    ) -> "PrematchDMPayload":
        data = payload.serialise()
        data["message"] = message
        return cls(data)


class AutoDraftPayload(WrapperBase):
    __slots__ = (
        "__team_a_captain",
        "__team_b_captain",
        "__team_a_players",
        "__team_b_players",
    )

    def __init__(self, data: dict):
        self.__team_a_captain: int = data["team_a_captain"]
        self.__team_b_captain: int = data["team_b_captain"]
        self.__team_a_players: List[int] = data["team_a_players"]
        self.__team_b_players: List[int] = data["team_b_players"]

    @property
    def team_a_captain(self) -> int:
        return self.__team_a_captain

    @property
    def team_b_captain(self) -> int:
        return self.__team_b_captain

    @property
    def team_a_players(self) -> List[int]:
        return self.__team_a_players

    @property
    def team_b_players(self) -> List[int]:
        return self.__team_b_players

    @classmethod
    def create(
        cls, captains: Tuple[int, int], players: Tuple[List[int], List[int]]
    ) -> "AutoDraftPayload":
        return cls(
            {
                "team_a_captain": captains[0],
                "team_b_captain": captains[1],
                "team_a_players": players[0],
                "team_b_players": players[1],
            }
        )

    def serialise(self) -> dict:
        return {
            "team_a_captain": self.__team_a_captain,
            "team_b_captain": self.__team_b_captain,
            "team_a_players": self.__team_a_players,
            "team_b_players": self.__team_b_players,
        }


class DMDeletePayload(WrapperBase):
    __slots__ = (
        "__guild_id",
        "__players",
    )

    def __init__(self, data: dict):
        self.__guild_id: int = data["guild_id"]
        self.__players: List[int] = data["players"]

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def players(self) -> List[int]:
        return self.__players

    def serialise(self) -> dict:
        return {
            "guild_id": self.__guild_id,
            "players": self.__players,
        }

    @classmethod
    def create(cls, *, guild_id: int, players: List[int]) -> "DMDeletePayload":
        return cls(
            {
                "guild_id": guild_id,
                "players": players,
            }
        )


class VCResetPayload(WrapperBase):
    __slots__ = (
        "__guild_id",
        "__lobby_vc_id",
        "__teams",
        "__queue_type",
    )

    def __init__(self, data: dict):
        self.__guild_id: int = data["guild_id"]
        self.__lobby_vc_id: int = data["lobby_vc_id"]
        self.__teams: List[MatchTeam] = data["teams"]
        self.__queue_type: QueueType = data["queue_type"]

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def lobby_vc_id(self) -> int:
        return self.__lobby_vc_id

    @property
    def teams(self) -> List[MatchTeam]:
        return self.__teams

    @property
    def queue_type(self) -> QueueType:
        return self.__queue_type

    def serialise(self) -> dict:
        return {
            "guild_id": self.__guild_id,
            "lobby_vc_id": self.__lobby_vc_id,
            "teams": self.__teams,
            "queue_type": self.__queue_type,
        }

    @classmethod
    def create(
        cls,
        guild_id: int,
        lobby_vc_id: int,
        teams: List[MatchTeam],
        queue_type: QueueType,
    ) -> "VCResetPayload":
        return cls(
            {
                "guild_id": guild_id,
                "lobby_vc_id": lobby_vc_id,
                "teams": teams,
                "queue_type": queue_type,
            }
        )


class MatchFinalisedPayload(WrapperBase):
    __slots__ = (
        "__guild_id",
        "__name",
        "__queue_type",
        "__owner_id",
        "__lobby_vc_id",
        "__winning_team",
        "__losing_team",
    )

    def __init__(self, data: dict):
        self.__guild_id: int = data["guild_id"]
        self.__name: str = data["name"]
        self.__queue_type: QueueType = data["queue_type"]
        self.__owner_id: int = data["owner_id"]
        self.__lobby_vc_id: int = data["lobby_vc_id"]
        self.__winning_team: MatchTeam = data["winning_team"]
        self.__losing_team: MatchTeam = data["losing_team"]

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def queue_type(self) -> QueueType:
        return self.__queue_type

    @property
    def owner_id(self) -> int:
        return self.__owner_id

    @property
    def lobby_vc_id(self) -> int:
        return self.__lobby_vc_id

    @property
    def teams(self) -> List[MatchTeam]:
        return [self.__winning_team, self.__losing_team]

    @property
    def winning_team(self) -> MatchTeam:
        return self.__winning_team

    @property
    def losing_team(self) -> MatchTeam:
        return self.__losing_team

    def serialise(self) -> dict:
        return {
            "guild_id": self.__guild_id,
            "name": self.__name,
            "queue_type": self.__queue_type,
            "owner_id": self.__owner_id,
            "lobby_vc_id": self.__lobby_vc_id,
            "winning_team": self.__winning_team,
            "losing_team": self.__losing_team,
        }

    @classmethod
    def create(
        cls,
        *,
        guild_id: int,
        name: str,
        queue_type: QueueType,
        owner_id: int,
        match_entry: MatchEntry,
    ) -> "MatchFinalisedPayload":
        return cls(
            {
                "guild_id": guild_id,
                "name": name,
                "queue_type": queue_type,
                "owner_id": owner_id,
                "lobby_vc_id": match_entry.voice_channel_id,
                "winning_team": match_entry.winning_team,
                "losing_team": match_entry.losing_team,
            }
        )


class SeasonEndPayload(WrapperBase):
    __slots__ = (
        "__guild_id",
        "__season",
        "__ranked_players",
    )

    def __init__(self, data: dict):
        self.__guild_id: int = data["guild_id"]
        self.__season: StatsSeason = data["season"]
        self.__ranked_players: Dict[QueueType, List[Tuple[int, StatsPlayer]]] = data[
            "ranked_players"
        ]

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def season(self) -> StatsSeason:
        return self.__season

    @property
    def ranked_players(self) -> Dict[QueueType, List[Tuple[int, StatsPlayer]]]:
        return self.__ranked_players

    def serialise(self) -> dict:
        return {
            "guild_id": self.__guild_id,
            "season": self.__season,
            "ranked_players": self.__ranked_players,
        }

    @classmethod
    def create(
        cls,
        *,
        guild_id: int,
        season: StatsSeason,
        ranked_players: Dict[QueueType, List[Tuple[int, StatsPlayer]]],
    ) -> "SeasonEndPayload":
        return cls(
            {
                "guild_id": guild_id,
                "season": season,
                "ranked_players": ranked_players,
            }
        )


class PlayerStatsResetPayload(WrapperBase):
    __slots__ = (
        "__user_id",
        "__guild_id",
        "__queue_type",
    )

    def __init__(self, data: dict):
        self.__user_id: int = data["user_id"]
        self.__guild_id: int = data["guild_id"]
        self.__queue_type: QueueType = data["queue_type"]

    @property
    def user_id(self) -> int:
        return self.__user_id

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def queue_type(self) -> QueueType:
        return self.__queue_type

    def serialise(self) -> dict:
        return {
            "user_id": self.__user_id,
            "guild_id": self.__guild_id,
            "queue_type": self.__queue_type,
        }

    @classmethod
    def create(
        cls, *, user_id: int, guild_id: int, queue_type: QueueType
    ) -> "PlayerStatsResetPayload":
        return cls(
            {
                "user_id": user_id,
                "guild_id": guild_id,
                "queue_type": queue_type,
            }
        )
