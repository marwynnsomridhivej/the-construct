from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Union
from warnings import deprecated

from base import WrapperBase
from canned import Canned
from exceptions import InvalidGuildID, PlayerAlreadyExists, PlayerDoesNotExist
from queuemanager import QueueType

__all__ = (
    "StatsWrapper",
    "StatsGuildContainer",
    "StatsSeason",
    "StatsInfo",
    "StatsPlayer",
)


class StatsWrapper(WrapperBase):
    __slots__ = ("__data",)

    def __init__(self, data: dict):
        self.__data: Dict[int, StatsGuildContainer] = {
            int(guild_id): StatsGuildContainer.parse(guild_containers)
            for guild_id, guild_containers in data.items()
        }

    def get(
        self, guild_id: int, throw: bool = False
    ) -> Union["StatsGuildContainer", None]:
        """Get a StatsGuildContainer (SGC) of the specified guild

        Args:
            guild_id (int): The guild ID of the guild
            throw (bool): Whether or not to throw an exception if a SGC instance is not found

        Raises:
            InvalidGuildID: No SGC instance exists for the specified guild

        Returns:
            Union[StatsGuildContainer, None]: The SGC instance of the specified guild
        """
        sgc = self.__data.get(guild_id)
        if sgc is None and throw:
            raise InvalidGuildID(guild_id)
        return sgc

    def get_or_create(self, guild_id: int) -> "StatsGuildContainer":
        """Get or create a StatsGuildContainer (SGC) for the specified guild

        Args:
            guild_id (int): The ID of the guild

        Returns:
            StatsGuildContainer: An existing SGC instance or a newly created blank instance
        """
        sgc = self.get(guild_id)
        if sgc is None:
            sgc = StatsGuildContainer.create_blank()
            self.__data[guild_id] = sgc
        return sgc

    @property
    def data(self) -> Dict[int, "StatsGuildContainer"]:
        return self.__data

    def serialise(self) -> dict:
        """Convert StatsWrapper instance representation into a dict

        Returns:
            dict: Dictionary representation of the StatsWrapper instance
        """
        return {guild_id: entry.serialise() for guild_id, entry in self.__data.items()}


class StatsGuildContainer(WrapperBase):
    __slots__ = (
        "current",
        "history",
    )

    def __init__(self, data: dict):
        self.current: Union[StatsSeason, None] = (
            StatsSeason.parse(data["current"])
            if data.get("current") is not None
            else None
        )
        self.history: List[StatsSeason] = [
            StatsSeason.parse(entry) for entry in data["history"]
        ]

    def has_active_season(self) -> bool:
        return isinstance(self.current, StatsSeason)

    def set_current_season(self, name: str) -> "StatsSeason":
        if self.has_active_season():
            raise ValueError("An active season already exists")

        self.current = StatsSeason.create_blank(name)

    def stop_current_season(self) -> None:
        if not self.has_active_season():
            raise ValueError("No active season exists")

        self.current.stop_season()
        self.history.append(self.current)
        self.current = None

    def serialise(self) -> dict:
        """Convert StatsGuildContainer (SGC) instance representation into a dict

        Returns:
            dict: Dictionary representation of the SGC instance
        """
        return {
            "current": self.current.serialise() if self.current else None,
            "history": [season.serialise() for season in self.history],
        }

    @classmethod
    def create_blank(cls) -> "StatsGuildContainer":
        return cls(
            {
                "current": None,
                "history": [],
            }
        )


class StatsSeason(WrapperBase):
    # TODO: Rename to StatsSeason
    __slots__ = (
        "name",
        "start_timestamp",
        "end_timestamp",
        "archived",
        "r6_5v5",
        "r6_1v1",
    )

    # Used to convert enum text to class attribute name
    __QT_ATTR_CONVERSION = {
        QueueType.R6_5V5: "r6_5v5",
        QueueType.R6_1V1: "r6_1v1",
    }

    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.start_timestamp: int = data["start_timestamp"]
        self.end_timestamp: int = data.get("end_timestamp", None)
        self.archived: bool = data["archived"]

        self.r6_5v5: StatsInfo = StatsInfo.parse(
            data[self.__QT_ATTR_CONVERSION[QueueType.R6_5V5]]
        )
        self.r6_1v1: StatsInfo = StatsInfo.parse(
            data[self.__QT_ATTR_CONVERSION[QueueType.R6_1V1]]
        )

    @property
    def is_current(self) -> bool:
        return not self.archived

    def get_data_by_queue_type(self, queue_type: QueueType) -> "StatsInfo":
        data = getattr(self, self.__QT_ATTR_CONVERSION[queue_type])
        assert isinstance(data, StatsInfo)
        return data

    def stop_season(self) -> None:
        self.end_timestamp = int(datetime.now().timestamp())
        self.archived = True

    def get_player(
        self, queue_type: QueueType, user_id: int, throw: bool = False
    ) -> Union["StatsPlayer", None]:
        """Get a StatsPlayer in the specified queue type with the specified user ID

        Args:
            queue_type (QueueType): The queue type to search
            user_id (int): The user ID of the desired StatsPlayer instance
            throw (bool): Whether or not to throw an exception if a StatsPlayer instance cannot be found

        Raises:
            PlayerDoesNotExist: No StatsPlayer instance exists in the specified queue type with the specified user ID

        Returns:
            Union[StatsPlayer, None]: The StatsPlayer instance, if found
        """
        data = self.get_data_by_queue_type(queue_type)
        player = data.players.get(user_id)
        if player is None and throw:
            raise PlayerDoesNotExist(user_id)
        return player

    def create_player(self, queue_type: QueueType, user_id: int) -> "StatsPlayer":
        """Create a StatsPlayer in the specified queue type with the specified user ID

        Args:
            queue_type (QueueType): The queue type to search
            user_id (int): The ID of the user

        Raises:
            PlayerAlreadyExists: A StatsPlayer already exists for the specified user

        Returns:
            StatsPlayer: A newly created StatsPlayer instance for the specified user in the specified queue type
        """
        data = self.get_data_by_queue_type(queue_type)
        if data.players.get(user_id) is not None:
            raise PlayerAlreadyExists(user_id)
        data.players[user_id] = StatsPlayer.create_zeroed(user_id)
        return data.players[user_id]

    def delete_player(self, queue_type: QueueType, user_id: int) -> None:
        """Deletes a StatsPlayer entry in the specified queue type for the specified user ID

        Args:
            queue_type (QueueType): The queue type to search
            user_id (int): The ID of the user

        Raises:
            PlayerDoesNotExist: No StatsPlayer exists in the specified queue type for the specified user ID
        """
        data = self.get_data_by_queue_type(queue_type)
        if data.players.get(user_id) is None:
            raise PlayerDoesNotExist(user_id)
        del data.players[user_id]

    def award_player(
        self,
        queue_type: QueueType,
        user_id: int,
        mvp: bool,
        win: bool,
        mu: float,
        sigma: float,
    ) -> None:
        """Awards the specified player points for winning or losing a match

        Args:
            queue_type (QueueType): The queue type to search
            user_id (int): The ID of the user
            mvp (bool): Whether or not the player was the team's MVP
            win (bool): Whether or not the player was on the winning team
            mu (float): The player's new OpenSkill mu
            sigma (float): The player's new OpenSkill sigma
        """
        try:
            player = self.get_player(queue_type, user_id, throw=True)
        except PlayerDoesNotExist:
            player = self.create_player(queue_type, user_id)

        player.award(win, mvp, mu, sigma)

    def serialise(self) -> dict:
        return {
            "name": self.name,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "archived": self.archived,
            "r6_5v5": self.r6_5v5.serialise(),
            "r6_1v1": self.r6_1v1.serialise(),
        }

    @classmethod
    def create_blank(cls, name: str) -> "StatsSeason":
        return cls(
            {
                "name": name,
                "start_timestamp": int(datetime.now().timestamp()),
                "end_timestamp": None,
                "archived": False,
                "r6_5v5": StatsInfo.create_blank().serialise(),
                "r6_1v1": StatsInfo.create_blank().serialise(),
            }
        )


class StatsInfo(WrapperBase):
    __slots__ = (
        "match_count",
        "players",
    )

    def __init__(self, data: dict):
        self.match_count: int = data["match_count"]

        assert isinstance(data["players"], dict)
        self.players: Dict[int, StatsPlayer] = {
            int(user_id): StatsPlayer.parse(entry)
            for user_id, entry in data["players"].items()
        }

    @property
    def player_count(self) -> int:
        return len(self.players.keys()) if self.players else 0

    def serialise(self) -> dict:
        """Convert StatsInfo instance representation into a dict

        Returns:
            dict: Dictionary representation of the StatsInfo instance
        """
        return {
            "match_count": self.match_count,
            "players": {
                user_id: player.serialise()
                for user_id, player in self.players.items()
                if player.matches_played > 0
            },
        }

    @classmethod
    def create_blank(cls) -> "StatsInfo":
        return cls({"match_count": 0, "players": {}})


class StatsPlayer(WrapperBase):
    __slots__ = (
        "id",
        "wins",
        "losses",
        "times_mvp",
        # OpenSkill
        "mu",
        "sigma",
        "max_ordinal",
        # Legacy
        "__points",
        "__max_points",
    )

    def __init__(self, data: dict):
        self.id: int = data["id"]
        self.wins: int = data["wins"]
        self.losses: int = data["losses"]
        self.times_mvp: int = data["times_mvp"]

        # New v2.x+ OpenSkill rating parameters.
        # These values can be None when handling v1.x data
        self.mu: Union[float, None] = data.get("mu", 25)
        self.sigma: Union[float, None] = data.get("sigma", 25 / 3)
        self.max_ordinal: Union[float, None] = data.get("max_ordinal", 0)

        # Legacy v1.x points system
        self.__points: Union[int, None] = data.get("points")
        self.__max_points: Union[int, None] = data.get("max_points")

    # ======================================
    # ======OPENSKILL V2.X+ ATTRIBUTES======
    # ======================================

    @property
    def ordinal(self) -> float:
        """The StatsPlayer's OpenSkill ordinal, used in the backend for
        leaderboard rankings.

        Returns:
            float: mu - 3 * sigma
        """
        return self.mu - 3 * self.sigma

    @property
    def rating(self) -> Decimal:
        """The StatsPlayer's visible rating. Should be player-facing
        only, and not used internally

        Returns:
            Decimal: 50 + 3 * ordinal, rounded to two decimal places
        """
        return Decimal(50 + 3 * self.ordinal).quantize(Decimal("0.01"))

    @property
    def max_rating(self) -> Decimal:
        """The StatsPlayer's peak visible rating. Should be player-facing only,
        and not used internally

        Returns:
            Decimal: Peak visible rating achieved, rounded to two decimal places
        """
        return Decimal(50 + 3 * self.max_ordinal).quantize(Decimal("0.01"))

    # ==================================
    # ======LEGACY V1.X ATTRIBUTES======
    # ==================================

    @property
    def is_legacy(self) -> bool:
        return self.__points is not None and self.__max_points is not None

    @property
    @deprecated(Canned.DEPR_V1X_POINTS)
    def points(self) -> Union[int, None]:
        return self.__points

    @property
    @deprecated(Canned.DEPR_V1X_POINTS)
    def max_points(self) -> Union[int, None]:
        return self.__max_points

    # =================================
    # =========UTIL PROPERTIES=========
    # =================================

    @property
    def matches_played(self) -> int:
        return self.wins + self.losses

    @property
    def wl_ratio(self) -> Decimal:
        return (
            Decimal("{:.2f}".format(self.wins / self.matches_played))
            if self.matches_played > 0
            else Decimal()
        )

    def __eq__(self, other: "StatsPlayer") -> bool:
        return all(
            [
                getattr(self, attr) == getattr(other, attr)
                for attr in [
                    "id",
                    "wins",
                    "losses",
                    "times_mvp",
                    # OpenSkill v2.x+
                    "mu",
                    "sigma",
                    "max_ordinal",
                    # Legacy v1.x
                    "points",
                    "max_points",
                ]
            ]
        )

    def __ne__(self, other: "StatsPlayer") -> bool:
        return not self == other

    def award(self, win: bool, mvp: bool, mu: float, sigma: float) -> Decimal:
        """Awards the player and adjusts values accordingly

        Args:
            win (bool): Whether or not the player was on the winning team
            mvp (bool): Whether or not the player was the team MVP
            mu (float): The player's new OpenSkill mu
            sigma (float): The player's new OpenSkill sigma

        Returns:
            Decimal: The change in the player's rating
        """
        if win:
            self.wins += 1
        else:
            self.losses += 1

        if mvp:
            self.times_mvp += 1

        previous = self.ordinal

        self.mu = mu
        self.sigma = sigma

        current = self.ordinal

        if self.ordinal > self.max_ordinal:
            self.max_ordinal = self.ordinal

        return Decimal(current - previous)

    def reset(self) -> None:
        """Reset a player's win, loss, mvp, and OpenSkill rating"""
        self.wins = 0
        self.losses = 0
        self.times_mvp = 0
        self.mu = 25
        self.sigma = 25 / 3
        self.max_ordinal = 0

    def serialise(self) -> dict:
        """Convert StatsPlayer instance representation into a dict

        Returns:
            dict: Dictionary representation of the StatsPlayer instance
        """
        data = {
            "id": self.id,
            "wins": self.wins,
            "losses": self.losses,
            "times_mvp": self.times_mvp,
        }

        if self.is_legacy:
            # Return legacy format if v1.x data only
            data["points"] = self.__points
            data["max_points"] = self.__max_points
        else:
            # Use OpenSkill for v2.x+
            data["mu"] = self.mu
            data["sigma"] = self.sigma
            data["max_ordinal"] = self.max_ordinal

        return data

    @classmethod
    def create_zeroed(cls, user_id: int) -> "StatsPlayer":
        """Creates a zeroed StatsPlayer instance

        Args:
            user_id (int): The ID of the user

        Returns:
            StatsPlayer: The created zeroed instance
        """
        return cls.parse(
            {
                "id": user_id,
                "wins": 0,
                "losses": 0,
                "times_mvp": 0,
                # OpenSkill
                "mu": 25,
                "sigma": 25 / 3,
                "max_ordinal": 0,
            }
        )
