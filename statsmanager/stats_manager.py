import copy

import discord
from openskill.models import PlackettLuce, PlackettLuceRating

from base import ManagerBase
from exceptions import PlayerDoesNotExist
from queuemanager import QueueType

from .stats import StatsPlayer, StatsSeason, StatsWrapper

__all__ = ("StatsManager",)


class StatsManager(ManagerBase):
    def __init__(self, stats_loc: str):
        super().__init__(stats_loc, "stats")

        # Initialise the OpenSkill model
        self.model: PlackettLuce = PlackettLuce(
            limit_sigma=True,
            margin=4,
            weight_bounds=(1, 1.225),
        )

    async def load(self):
        await super()._load(name="StatsManager")

    # =====================================
    # ============PLAYERS STUFF============
    # =====================================
    async def get_or_create_wrapper(self) -> StatsWrapper:
        return await super()._get_or_create_wrapper(cls=StatsWrapper)

    async def get_or_create_player(
        self, *, guild_id: int, queue_type: QueueType, user_id: int
    ) -> StatsPlayer:
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)
        assert sgc.current is not None

        try:
            player = sgc.current.get_player(queue_type, user_id, throw=True)
        except PlayerDoesNotExist:
            player = sgc.current.create_player(queue_type, user_id)
            await self.write(wrapper)

        return player

    async def get_guild_players(
        self, guild_id: int, queue_type: QueueType
    ) -> list[StatsPlayer]:
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)
        assert sgc.current is not None

        return [
            player
            for player in sgc.current.get_data_by_queue_type(
                queue_type
            ).players.values()
        ]

    async def reset_player(
        self, *, guild_id: int, queue_type: QueueType, user_id: int
    ) -> None:
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)
        assert sgc.current is not None

        sgc.current.get_player(queue_type, user_id, throw=True).reset()
        await self.write(wrapper)

    async def delete_player(
        self, *, guild_id: int, queue_type: QueueType, user_id: int
    ) -> None:
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)
        assert sgc.current is not None

        sgc.current.delete_player(queue_type, user_id)
        await self.write(wrapper)

    async def award_team(
        self,
        *,
        guild_id: int,
        queue_type: QueueType,
        ratings: list[PlackettLuceRating],
        mvp_id: int,
        win: bool,
    ):
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)
        assert sgc.current is not None

        for rating in ratings:
            assert rating.name is not None

            player_id = int(rating.name)
            sgc.current.award_player(
                queue_type,
                player_id,
                mvp_id == player_id,
                win,
                rating.mu,
                rating.sigma,
            )
        await self.write(wrapper)

    # =====================================
    # ============SEASONS STUFF============
    # =====================================
    async def ensure_season(self, *, guild_id: int) -> None:
        """Ensures the specified guild has an active season, or if the named one exists

        Args:
            guild_id (int): The ID of the guild

        Raises:
            ValueError: No active season exists for the specified guild
        """
        wrapper = await self.get_or_create_wrapper()
        exists = wrapper.get_or_create(guild_id).has_active_season()
        err = ValueError(f"No active season for guild ID {guild_id}")
        if not exists:
            raise err

    async def start_season(self, *, guild_id: int, name: str) -> StatsSeason:
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)
        sgc.set_current_season(name)
        await self.write(wrapper)
        assert sgc.current is not None

        return sgc.current

    async def stop_season(self, *, guild_id: int) -> None:
        wrapper = await self.get_or_create_wrapper()
        wrapper.get_or_create(guild_id).stop_current_season()
        await self.write(wrapper)

    async def get_season(
        self, *, guild_id: int, name: str | None = None
    ) -> StatsSeason:
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)

        # If no name specified, return current season details
        if name is None:
            assert sgc.current is not None

            return sgc.current

        # Find first instance of season which matches the specified name
        seasons = copy.deepcopy(sgc.history)
        if isinstance(sgc.current, StatsSeason):
            seasons.insert(0, sgc.current)

        first_match_season = discord.utils.find(lambda s: s.name == name, seasons)
        assert first_match_season is not None

        return first_match_season

    async def get_season_rankings(
        self, *, guild_id: int, queue_type: QueueType, name: str | None = None
    ) -> list[tuple[int, StatsPlayer]]:
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)

        # Get appropriate season
        if name is None:
            season = sgc.current
        else:
            name = name.lower()
            seasons = copy.deepcopy(sgc.history)
            if isinstance(sgc.current, StatsSeason):
                seasons.insert(0, sgc.current)
            season = discord.utils.find(lambda s: s.name == name, seasons)

        # If season not found and name was specified, raise ValueError
        if season is None:
            raise ValueError(f'No season exists with the name "{name}"')

        players = [
            p for p in season.get_data_by_queue_type(queue_type).players.values()
        ]

        # Sort player list by highest to lowest by points
        # Point tiebreak handled by win loss ratio
        # Win loss ratio tiebreak handled by matches played
        players.sort(
            key=lambda p: (
                p.ordinal if not p.is_legacy else p.points,
                p.times_mvp,
                p.wl_ratio,
                p.matches_played,
            ),
            reverse=True,
        )

        previous_rating = None
        previous_rank = None
        rank_ordered = []
        for rank, player in enumerate(players, 1):
            # Get rating attribute based on legacy
            attr = player.ordinal if not player.is_legacy else player.points

            # Initialise the previous rating if not set
            if previous_rating is None:
                previous_rating = attr

            # Initialise the previous rank if not set
            if previous_rank is None:
                previous_rank = rank

            # Check if current player has same rating as previous. If so, reuse previous rank number
            if attr == previous_rating:
                rank_ordered.append((previous_rank, player))
                continue

            # Otherwise, append true rank and player, update previous rating and rank
            rank_ordered.append((rank, player))
            previous_rating = attr
            previous_rank = rank

        return rank_ordered

    async def get_all_seasons(self, guild_id: int) -> list[StatsSeason]:
        wrapper = await self.get_or_create_wrapper()

        current = wrapper.get_or_create(guild_id).current
        seasons = copy.deepcopy(wrapper.get_or_create(guild_id).history)
        if isinstance(current, StatsSeason):
            seasons.insert(0, current)

        return seasons

    async def increment_season_match_count(
        self, guild_id: int, queue_type: QueueType
    ) -> None:
        wrapper = await self.get_or_create_wrapper()
        sgc = wrapper.get_or_create(guild_id)
        assert sgc.current is not None

        sgc.current.get_data_by_queue_type(queue_type).match_count += 1
        await self.write(wrapper)
