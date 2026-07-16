from datetime import datetime

from base import ManagerBase
from event import AutoDraftPayload, MatchPayload

from .enums import R6Map, R6Side
from .match import MatchEntry, MatchTeam, MatchWrapper


class MatchManager(ManagerBase):
    """Database manager to manage match-related data."""

    def __init__(self, match_loc: str):
        super().__init__(match_loc, "matches")

    async def load(self):
        """Create the necessary directories and load into memory."""
        await super()._load(name="MatchManager")

    async def get_or_create_wrapper(self) -> MatchWrapper:
        """Get or create the MatchWrapper.

        Returns:
            MatchWrapper: The MatchWrapper instance.
        """
        return await super()._get_or_create_wrapper(cls=MatchWrapper)

    def get_starting_side(
        self, team: MatchTeam, captain_id: int, choice: R6Side
    ) -> R6Side:
        """Obtain the starting side assignment for a given team.

        Args:
            team (MatchTeam): The team to obtain the starting side assignment.
            captain_id (int): The user ID of the captain to test against.
            choice (R6Side): The starting side for the team of the captain
                whose user ID is provided in the `captain_id` argument.

        Returns:
            R6Side: The starting side assignment of the provided `team`.
        """
        flip = {
            R6Side.ATTACKER: R6Side.DEFENDER,
            R6Side.DEFENDER: R6Side.ATTACKER,
        }
        return choice if team.captain_id == captain_id else flip[choice]

    async def create_match(
        self, *, payload: MatchPayload, auto_draft: AutoDraftPayload | None = None
    ) -> None:
        """Create a match entry in the database from the provided payloads.

        Args:
            payload (MatchPayload): The MatchPayload obtained from the
                prematch setup.
            auto_draft (AutoDraftPayload | None, optional): The AutoDraftPayload
                obtained from the prematch setup. Defaults to None.
        """
        wrapper = await self.get_or_create_wrapper()

        # Init two empty teams
        team_a = MatchTeam.create_empty("A")
        team_b = MatchTeam.create_empty("B")

        if payload.auto_draft and auto_draft is not None:
            # Assign captains to each team from auto draft payload
            team_a.assign_captain(auto_draft.team_a_captain)
            team_b.assign_captain(auto_draft.team_b_captain)
            payload.set_auto_draft_captains(auto_draft)

            # Draft players to each team
            for team, players in [
                (team_a, auto_draft.team_a_players),
                (team_b, auto_draft.team_b_players),
            ]:
                for player_id in players:
                    team.draft_player(player_id)
        else:
            # Assign captains from payload
            team_a.assign_captain(payload.captains[0])
            team_b.assign_captain(payload.captains[1])

        # Craft entry data
        match_entry_data = {
            "created_timestamp": int(datetime.now().timestamp()),
            "type": payload.queue_entry.type,
            "voice_channel_id": payload.voice_channel_id,
            "team_a": team_a.serialise(),
            "team_b": team_b.serialise(),
            "map": None,
        }

        # Create match entry
        wrapper.get_or_create(payload.guild_id).create(
            payload.match_name,
            match_entry_data,
        )

        # Write to disk
        await self.write(wrapper)

    async def delete_match(self, guild_id: int, name: str) -> None:
        """Delete a match entry in the database from the provided
        guild ID and name.

        Args:
            guild_id (int): The guild ID to search for the match entry.
            name (str): The name of the match.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).delete(name)
        await self.write(wrapper)

    async def get_match(self, guild_id: int, name: str) -> MatchEntry:
        """Get a match entry in the database from the provided
        guild ID and name.

        Args:
            guild_id (int): The guild ID to search for the match.
            name (str): The name of the match.

        Returns:
            MatchEntry: The corresponding MatchEntry instance.
        """
        wrapper = await self.get_or_create_wrapper()
        return wrapper.get(guild_id, throw=True).get(name, throw=True)

    async def has_running_match(self, guild_id: int) -> bool:
        """Check whether or not a guild currently has actively running
        matches.

        Args:
            guild_id (int): The ID of the guild to search.

        Returns:
            bool: Whether or not active matches were found.
        """
        wrapper = await self.get_or_create_wrapper()
        return bool(wrapper.get(guild_id, throw=True).data)

    async def draft_player(
        self, guild_id: int, name: str, captain_id: int, player_id: int
    ) -> None:
        """Draft a player to the a team.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            name (str): The name of the match.
            captain_id (int): The user ID of the captain doing the draft.
            player_id (int): The user ID of the player the captain is
                attempting to draft.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).get_team_of_user(
            captain_id
        ).draft_player(player_id)
        await self.write(wrapper)

    async def ban_map(
        self, guild_id: int, name: str, captain_id: int, choice: R6Map
    ) -> None:
        """Ban a map.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            name (str): The name of the match.
            captain_id (int): The user ID of the captain selecting the map
                to ban.
            choice (R6Map): The selected map to be banned.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).ban_map(
            captain_id, choice
        )
        await self.write(wrapper)

    async def select_map(self, guild_id: int, name: str, choice: R6Map) -> None:
        """Set the map the match will be played on.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            name (str): The name of the match.
            choice (R6Map): The selected map to be played.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).set_map(choice)
        await self.write(wrapper)

    async def select_starting_side(
        self, guild_id: int, name: str, captain_id: int, choice: R6Side
    ) -> None:
        """Assign opposite starting sides (attack/defense) for both teams.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            name (str): The name of the match.
            captain_id (int): The user ID of the captain that chose their
                starting side.
            choice (R6Side): The chosen starting side of the captain with an
                ID corresponding to the provided `captain_id`.
        """
        wrapper = await self.get_or_create_wrapper()
        mgc = wrapper.get(guild_id, throw=True).get(name, throw=True)
        mgc.team_a.starting_side = self.get_starting_side(
            mgc.team_a, captain_id, choice
        )
        mgc.team_b.starting_side = self.get_starting_side(
            mgc.team_b, captain_id, choice
        )
        await self.write(wrapper)

    async def designate_mvp(self, guild_id: int, name: str, mvp_id: int) -> None:
        """Designate a user as their team's MVP.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            name (str): The name of the match.
            mvp_id (int): The user ID of the player to be designated their
                team's MVP.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).designate_mvp(mvp_id)
        await self.write(wrapper)

    async def set_winning_team(self, guild_id: int, name: str, captain_id: int) -> None:
        """Set the winning team.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            name (str): The name of the match.
            captain_id (int): The user ID of the captain of the winning team.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).designate_winner(
            captain_id
        )
        await self.write(wrapper)

    async def set_team_rounds_won(
        self, guild_id: int, name: str, captain_id: int, rounds_won: int
    ) -> None:
        """Set the amount of rounds won over the course of the match for
        a given team.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            name (str): The name of the match.
            captain_id (int): The user ID of the captain of the team to report
                their amount of rounds won.
            rounds_won (int): The amount of rounds won by the team.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).set_rounds_won(
            captain_id, rounds_won
        )
        await self.write(wrapper)

    async def set_team_vc(
        self, guild_id: int, name: str, captain_id: int, vc_id: int
    ) -> None:
        """Set the team's voice channel to the specified channel ID.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            name (str): The name of the match.
            captain_id (int): The user ID of the captain of the team.
            vc_id (int): The ID of the voice channel to be set.
        """
        wrapper = await self.get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).get_team_of_user(
            captain_id
        ).voice_channel_id = vc_id
        await self.write(wrapper)

    async def reset_draft(self, guild_id: int, payload: MatchPayload) -> None:
        """Reset a match's draft state completely.

        Args:
            guild_id (int): The ID of the guild the match is taking place in.
            payload (MatchPayload): The MatchPayload obtained after prematch
                setup was completed.
        """
        wrapper = await self.get_or_create_wrapper()
        entry = wrapper.get(guild_id, throw=True).get(payload.match_name, throw=True)
        entry.reset_draft(auto_draft=payload.auto_draft)
        entry.map = None
        await self.write(wrapper)
