from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from openskill.models import PlackettLuceRating

from canned import Canned
from event import Event, MatchFinalisedPayload
from queuemanager import QueueType
from ui import LeaderboardView
from util import EventHandlerType, ephemeral

if TYPE_CHECKING:
    from bot import Bot


class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot

    async def cog_load(self):
        _handlers: dict[EventHandlerType, Event] = {
            self.calc_stats: Event.MATCH_FINALISED,
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[StatsCog] Successfully loaded")

    async def _create_openskill_rating_object(
        self, guild_id: int, user_id: int, queue_type: QueueType
    ) -> PlackettLuceRating:
        player = await self.bot.stats_manager.get_or_create_player(
            guild_id=guild_id,
            queue_type=queue_type,
            user_id=user_id,
        )
        return self.bot.stats_manager.model.create_rating(
            [player.mu, player.sigma], name=f"{user_id}"
        )

    async def calc_stats(self, payload: MatchFinalisedPayload):
        # Typehint assertions for attributes that should already have values
        assert (
            payload.winning_team.mvp_id is not None
            and payload.winning_team.rounds_won is not None
            and payload.losing_team.mvp_id is not None
            and payload.losing_team.rounds_won is not None
        )

        # Create rating objects from StatsPlayer mu and sigma for both teams
        winning_team: list[PlackettLuceRating] = [
            await self._create_openskill_rating_object(
                payload.guild_id,
                player_id,
                payload.queue_type,
            )
            for player_id in payload.winning_team.players
        ]
        losing_team: list[PlackettLuceRating] = [
            await self._create_openskill_rating_object(
                payload.guild_id,
                player_id,
                payload.queue_type,
            )
            for player_id in payload.losing_team.players
        ]

        # Create weights to designate MVP performance
        winning_weights = [
            10
            if payload.winning_team.mvp_id is None
            or player_id != payload.winning_team.mvp_id
            else 11.625
            for player_id in payload.winning_team.players
        ]
        losing_weights = [
            10
            if payload.losing_team.mvp_id is None
            or player_id != payload.losing_team.mvp_id
            else 11.625
            for player_id in payload.losing_team.players
        ]

        # Rate all players in the match
        new_winning_team_rating, new_losing_team_rating = (
            self.bot.stats_manager.model.rate(
                [winning_team, losing_team],
                scores=[
                    payload.winning_team.rounds_won,
                    payload.losing_team.rounds_won,
                ],
                weights=[winning_weights, losing_weights],
            )
        )

        # Update stats
        await self.bot.stats_manager.award_team(
            guild_id=payload.guild_id,
            queue_type=payload.queue_type,
            ratings=new_winning_team_rating,
            mvp_id=payload.winning_team.mvp_id,
            win=True,
        )
        await self.bot.stats_manager.award_team(
            guild_id=payload.guild_id,
            queue_type=payload.queue_type,
            ratings=new_losing_team_rating,
            mvp_id=payload.losing_team.mvp_id,
            win=False,
        )

    @app_commands.command(name="leaderboard", description="View the server leaderboard")
    @app_commands.describe(
        name="The name of the season you would like to view rankings for"
    )
    @app_commands.rename(queue_type="type")
    @app_commands.guild_only()
    async def _leaderboard_command(
        self,
        interaction: discord.Interaction,
        name: str | None = None,
        queue_type: QueueType = QueueType.R6_5V5,
    ):
        # Typehint assert, we know this is true anyway
        assert (guild_id := interaction.guild_id) is not None

        # Ensure an active season exists if not named
        try:
            if name is None:
                await self.bot.stats_manager.ensure_season(guild_id=guild_id)
        except ValueError:
            return await interaction.response.send_message(
                Canned.ERR_SEASON_NO_EXISTS, **ephemeral()
            )

        # Ensure we have rankings and the season isn't empty (aka stats exist)
        try:
            ranked_players = await self.bot.stats_manager.get_season_rankings(
                guild_id=guild_id, queue_type=queue_type, name=name
            )
        except ValueError:
            return await interaction.response.send_message(
                Canned.ERR_STATS_INVALID_SEASON_NAME, **ephemeral()
            )
        else:
            if not ranked_players:
                return await interaction.response.send_message(
                    Canned.ERR_STATS_NO_PLAYERS, **ephemeral()
                )

        lbview = LeaderboardView(
            source_interaction=interaction,
            queue_type=queue_type,
            season=await self.bot.stats_manager.get_season(
                guild_id=guild_id, name=name.lower() if name else None
            ),
            rankings=ranked_players,
        )
        lbview.init_components()

        await interaction.response.send_message(
            view=lbview, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True
        )

    @_leaderboard_command.autocomplete("name")
    async def _leaderboard_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        # Typehint assert, we know this is true anyway
        assert (guild_id := interaction.guild_id) is not None

        seasons = await self.bot.stats_manager.get_all_seasons(guild_id)
        return sorted(
            [
                app_commands.Choice(name=s.name.title(), value=s.name)
                for s in seasons
                if current.lower() in s.name
            ],
            key=lambda c: c.name,
        )


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
