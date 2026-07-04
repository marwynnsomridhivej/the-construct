from typing import Literal, overload

from base import WrapperBase
from exceptions import (
    CaptainAlreadyAssigned,
    CaptainNotAssigned,
    InvalidGuildID,
    MapAlreadyBanned,
    MatchAlreadyExists,
    MatchDoesNotExist,
    MatchFinalised,
    MVPAlreadyAssigned,
)
from queuemanager import QueueType

from .enums import R6Map, R6Side

__all__ = (
    "MatchWrapper",
    "MatchGuildContainer",
    "MatchEntry",
    "MatchTeam",
)


class MatchWrapper(WrapperBase):
    __slots__ = ("__data",)

    def __init__(self, data: dict):
        self.__data: dict[int, MatchGuildContainer] = {
            int(guild_id): MatchGuildContainer.parse(guild_containers)
            for guild_id, guild_containers in data.items()
        }

    @overload
    def get(self, guild_id: int, *, throw: Literal[True]) -> "MatchGuildContainer": ...

    @overload
    def get(
        self, guild_id: int, *, throw: Literal[False]
    ) -> "MatchGuildContainer | None": ...

    @overload
    def get(self, guild_id: int) -> "MatchGuildContainer | None": ...

    def get(self, guild_id: int, throw: bool = False) -> "MatchGuildContainer | None":
        """Get a MatchGuildContainer (MGC) of the specified guild

        Args:
            guild_id (int): The guild ID of the guild
            throw (bool): Whether or not to throw an exception if an MGC instance is not found

        Raises:
            InvalidGuildID: No MGC instance exists for the specified guild

        Returns:
            MatchGuildContainer | None: The MGC instance of the specified guild
        """
        mgc = self.__data.get(guild_id)
        if mgc is None and throw:
            raise InvalidGuildID(guild_id)
        return mgc

    def get_or_create(self, guild_id: int) -> "MatchGuildContainer":
        """Get or create a MatchGuildContainer (MGC) for the specified guild

        Args:
            guild_id (int): The ID of the guild

        Returns:
            MatchGuildContainer: An existing MGC instance or a newly created blank instance
        """
        mgc = self.get(guild_id)
        if mgc is None:
            mgc = MatchGuildContainer({})
            self.__data[guild_id] = mgc
        return mgc

    @property
    def data(self) -> dict[int, "MatchGuildContainer"]:
        return self.__data

    def serialise(self) -> dict:
        """Convert MatchWrapper instance representation into a dict

        Returns:
            dict: Dictionary representation of the MatchWrapper instance
        """
        return {guild_id: mgc.serialise() for guild_id, mgc in self.__data.items()}


class MatchGuildContainer(WrapperBase):
    __slots__ = ("__data",)

    def __init__(self, data: dict):
        self.__data: dict[str, MatchEntry] = {
            name: MatchEntry.parse(entry) for name, entry in data.items()
        }

    @overload
    def get(self, name: str, throw: Literal[True]) -> "MatchEntry": ...

    @overload
    def get(self, name: str, throw: Literal[False]) -> "MatchEntry | None": ...
    
    @overload
    def get(self, name: str) -> "MatchEntry | None": ...

    def get(self, name: str, throw: bool = False) -> "MatchEntry | None":
        """Get a MatchEntry with the specified name

        Args:
            name (str): The name of the desired MatchEntry instance
            throw (bool): Whether or not to throw an exception if a MatchEntry instance is not found

        Raises:
            MatchDoesNotExist: No MatchEntry instance exists with the specified name

        Returns:
            MatchEntry | None: The MatchEntry instance with the specified name
        """
        data = self.__data.get(name)
        if data is None and throw:
            raise MatchDoesNotExist(name)
        return data

    def create(self, name: str, data: dict) -> None:
        """Create a MatchEntry with specified name and data

        Args:
            name (str): The name of the match
            data (dict): The attributes of the match

        Raises:
            MatchAlreadyExists: Exception thrown when name is already in use
        """
        if self.__data.get(name) is not None:
            raise MatchAlreadyExists(name)
        self.__data[name] = MatchEntry.parse(data)

    def delete(self, name: str) -> "MatchEntry":
        """Delete a MatchEntry with the specified name

        Args:
            name (str): The name of the match

        Raises:
            MatchDoesNotExist: No MatchEntry instance exists with the specified name

        Returns:
            MatchEntry: MatchEntry instance that has been deleted
        """
        match_entry = self.__data.get(name)
        if match_entry is None:
            raise MatchDoesNotExist(name)

        return self.__data.pop(name)

    @property
    def data(self) -> dict[str, "MatchEntry"]:
        return self.__data

    def serialise(self) -> dict:
        """Convert MatchGuildContainer (MGC) instance representation into a dict

        Returns:
            dict: Dictionary representation of the MGC instance
        """
        return {name: entry.serialise() for name, entry in self.__data.items()}


class MatchEntry(WrapperBase):
    __slots__ = (
        "created_timestamp",
        "type",
        "voice_channel_id",
        "team_a",
        "team_b",
        "map",
    )

    def __init__(self, data: dict):
        self.created_timestamp: int = data["created_timestamp"]
        self.type: QueueType = data["type"]
        self.voice_channel_id: int = data["voice_channel_id"]

        self.team_a: MatchTeam = MatchTeam.parse(data["team_a"])
        self.team_b: MatchTeam = MatchTeam.parse(data["team_b"])
        self.map: R6Map | None = data["map"]

    def get_team_of_user(self, user_id: int) -> "MatchTeam":
        """Finds the team the specified user ID belongs to

        Args:
            user_id (int): The ID of the user to search for

        Returns:
            MatchTeam: The team the user belongs to
        """
        return self.team_a if user_id in self.team_a.players else self.team_b

    def designate_winner(self, captain_id: int) -> None:
        """Designate winner by captain_id. The losing team is also automatically set

        Args:
            captain_id (int): The ID of the captain on the winning team

        Raises:
            MatchFinalised: The match has been finalised and results cannot be modified
        """
        if self.wins_set:
            raise MatchFinalised

        self.team_a.win = self.team_a.captain_id == captain_id
        self.team_b.win = not self.team_a.win

    def designate_mvp(self, mvp_id: int) -> None:
        """Designates a team's MVP

        Args:
            mvp_id (int): The user ID of the team MVP

        Raises:
            MatchFinalised: The match has been finalised and results cannot be modified
            MVPAlreadyAssigned: The team the user is on already has an MVP assigned
        """
        if self.mvps_set:
            raise MatchFinalised

        self.get_team_of_user(mvp_id).designate(mvp_id)

    def ban_map(self, captain_id: int, choice: R6Map) -> None:
        """Ban a map and add it to the respective team's map banned list

        Args:
            captain_id (int): The ID of the captain of the team
            choice (R6Map): The map to ban

        Raises:
            MapAlreadyBanned: The specified map has already been banned by one of the teams
        """
        if choice in self.banned_maps:
            raise MapAlreadyBanned

        self.get_team_of_user(captain_id).ban_map(choice)

    def set_map(self, choice: R6Map) -> None:
        """Sets the match's map to the choice provided

        Args:
            choice (R6Map): The map to be set

        Raises:
            MapAlreadyBanned: The specified map was banned by one of the teams
        """
        if choice in self.banned_maps:
            raise MapAlreadyBanned

        self.map = choice if isinstance(choice, R6Map) else R6Map(choice)

    def reset_draft(self, auto_draft: bool = False) -> None:
        """Resets the complete draft state for both teams

        Args:
            auto_draft (bool, optional): Whether or not auto draft was used. Defaults to False.
        """
        for team in [self.team_a, self.team_b]:
            # Do not reset draft if auto draft was used
            if not auto_draft:
                team.reset_player_draft()

            # Reset map bans, starting sides, and MVP designation
            team.reset_map_bans()
            team.reset_starting_side()
            team.reset_mvp_designation()

    def set_rounds_won(self, captain_id: int, rounds_won: int) -> None:
        self.get_team_of_user(captain_id).set_rounds_won(rounds_won)

    @property
    def captains(self) -> list[int]:
        if self.team_a.captain_id is None or self.team_b.captain_id is None:
            raise ValueError
        return [self.team_a.captain_id, self.team_b.captain_id]

    @property
    def banned_maps(self) -> list[R6Map]:
        return self.team_a.map_bans + self.team_b.map_bans

    @property
    def has_map(self) -> bool:
        return self.map is not None

    @property
    def sides_selected(self) -> bool:
        return (
            self.team_a.starting_side is not None
            and self.team_b.starting_side is not None
        )

    @property
    def mvps_set(self) -> bool:
        return isinstance(self.team_a.mvp_id, int) and isinstance(
            self.team_b.mvp_id, int
        )

    @property
    def wins_set(self) -> bool:
        return isinstance(self.team_a.win, bool) and isinstance(self.team_b.win, bool)

    @property
    def finalised(self) -> bool:
        return self.wins_set and self.mvps_set

    @property
    def winning_team(self) -> "MatchTeam | None":
        if not self.wins_set:
            return None

        return self.team_a if self.team_a.win else self.team_b

    @property
    def losing_team(self) -> "MatchTeam | None":
        if not self.wins_set:
            return None

        return self.team_a if self.team_b.win else self.team_b

    def serialise(self) -> dict:
        """Convert MatchEntry instance representation into a dict

        Returns:
            dict: Dictionary representation of the MatchEntry instance
        """
        return {
            "created_timestamp": self.created_timestamp,
            "type": self.type,
            "voice_channel_id": self.voice_channel_id,
            "team_a": self.team_a.serialise(),
            "team_b": self.team_b.serialise(),
            "map": self.map,
        }


class MatchTeam(WrapperBase):
    __slots__ = (
        "name",
        "voice_channel_id",
        "captain_id",
        "players",
        "map_bans",
        "starting_side",
        "win",
        "mvp_id",
        "rounds_won",
    )

    def __init__(self, data: dict):
        assert data["name"] in ["A", "B"]

        self.name: str = data["name"]
        self.voice_channel_id: int | None = data["voice_channel_id"]
        self.captain_id: int | None = data["captain_id"]
        self.players: list[int] = data["players"]
        self.map_bans: list[R6Map] = data["map_bans"]
        self.starting_side: R6Side | None = data["starting_side"]
        self.win: bool | None = data["win"]
        self.mvp_id: int | None = data["mvp_id"]
        self.rounds_won: int | None = data["rounds_won"]

    def assign_captain(self, user_id: int) -> None:
        """Designates a captain by user ID

        Args:
            user_id (int): The ID of the user to be made captain

        Raises:
            CaptainAlreadyAssigned: A team captain has already been designated
        """
        if self.captain_id is not None:
            raise CaptainAlreadyAssigned

        self.captain_id = user_id
        self.players.append(user_id)

    def draft_player(self, user_id: int) -> None:
        """Drafts a player to the team by user ID

        Args:
            user_id (int): The ID of the user to be drafted

        Raises:
            CaptainNotAssigned: A team captain has not been designated yet
        """
        if self.captain_id is None:
            raise CaptainNotAssigned

        self.players.append(user_id)

    def ban_map(self, choice: R6Map) -> None:
        """Bans a map by name

        Args:
            choice (R6Map): The map to ban
        """
        self.map_bans.append(choice)

    def designate(self, user_id: int) -> None:
        """Designates a player on the team as the MVP

        Args:
            user_id (int): The ID of the user to be made MVP

        Raises:
            MVPAlreadyAssigned: This team already has an MVP
        """
        if self.mvp_id is not None:
            raise MVPAlreadyAssigned

        self.mvp_id = user_id

    def reset_player_draft(self) -> None:
        """Resets the player draft state to default"""
        if self.captain_id is None:
            raise ValueError

        self.players = [self.captain_id]

    def reset_map_bans(self) -> None:
        """Resets the map ban state to default"""
        self.map_bans = []

    def reset_starting_side(self) -> None:
        """Resets the starting side state to default"""
        self.starting_side = None

    def reset_mvp_designation(self) -> None:
        """Resets the team's MVP designation"""
        self.mvp_id = None

    def set_rounds_won(self, rounds_won: int) -> None:
        """Set the amount of rounds won by this team

        Args:
            score (int): The amount of rounds this team won in total
        """
        self.rounds_won = rounds_won

    def serialise(self) -> dict:
        """Convert MatchTeam instance representation into a dict

        Returns:
            dict: Dictionary representation of the MatchTeam instance
        """
        return {
            "name": self.name,
            "voice_channel_id": self.voice_channel_id,
            "captain_id": self.captain_id,
            "players": self.players,
            "map_bans": self.map_bans,
            "starting_side": self.starting_side,
            "win": self.win,
            "mvp_id": self.mvp_id,
            "rounds_won": self.rounds_won,
        }

    @classmethod
    def create_empty(cls, a_or_b: str) -> "MatchTeam":
        """Creates a blank MatchTeam instance

        Returns:
            MatchTeam: The created blank instance
        """
        return cls(
            {
                "name": a_or_b,
                "voice_channel_id": None,
                "captain_id": None,
                "players": [],
                "map_bans": [],
                "starting_side": None,
                "win": None,
                "mvp_id": None,
                "rounds_won": None,
            }
        )
