from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, List, Tuple

import discord

from canned import Canned
from exceptions import RoundsWonTeamWonMismatch
from matchmanager import MatchTeam

if TYPE_CHECKING:
    from ...views import R6View

__all__ = ("R6ResultModal",)


class R6ResultModal(discord.ui.Modal):
    def __init__(self, *, view):
        super().__init__(title="Report Results")
        self.r6view: R6View = view

        # Typehints
        self.result: discord.ui.Label
        self.team_a_rounds_won: discord.ui.Label
        self.team_b_rounds_won: discord.ui.Label

        for item in self.init_components():
            self.add_item(item)

        # Validity flag
        self.is_valid: bool = True

    def init_components(self) -> List[discord.ui.Item]:
        # Select which team won overall
        self.result = discord.ui.Label(
            text="Match Results",
            description="Select the winning team",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(
                        label=f"Team {self.get_captain_name(team)}",
                        value=team.captain_id,
                    )
                    for team in self.r6view.teams
                ],
                required=True,
            ),
        )

        # Enter how many rounds each team won throughout the match
        self.team_a_rounds_won, self.team_b_rounds_won = [
            discord.ui.Label(
                text=f"Rounds Won - Team {self.get_captain_name(team)}",
                description="Enter how many rounds this team won",
                component=discord.ui.TextInput(
                    min_length=1,
                    max_length=2,
                    placeholder="Enter rounds won here",
                    required=True,
                ),
            )
            for team in self.r6view.teams
        ]

        # Return list of all components
        return [
            self.result,
            self.team_a_rounds_won,
            self.team_b_rounds_won,
        ]

    def get_captain_name(self, team: MatchTeam) -> str:
        return (
            self.r6view.bot.get_guild(self.r6view.payload.guild_id)
            .get_member(team.captain_id)
            .display_name
        )

    def get_rounds_won(self, winning_captain_id: int) -> Tuple[int, int]:
        assert isinstance(self.team_a_rounds_won.component, discord.ui.TextInput)
        assert isinstance(self.team_b_rounds_won.component, discord.ui.TextInput)

        # Ensure no decimal points
        if any(
            [
                "." in component.value
                for component in [
                    self.team_a_rounds_won.component,
                    self.team_b_rounds_won.component,
                ]
            ]
        ):
            raise ValueError

        # Cast string to int (will raise ValueError if any invalid characters are present)
        rounds_won_a = int(self.team_a_rounds_won.component.value)
        rounds_won_b = int(self.team_b_rounds_won.component.value)

        # Ensure the user enters two positive integer value
        if rounds_won_a < 0 or rounds_won_b < 0:
            raise ValueError

        # Find winning team
        winning_team = discord.utils.find(
            lambda t: t.captain_id == winning_captain_id, self.r6view.teams
        )

        # Ensure winning team won more rounds
        if self.r6view.teams.index(winning_team) == 0 and rounds_won_a <= rounds_won_b:
            raise RoundsWonTeamWonMismatch
        elif (
            self.r6view.teams.index(winning_team) == 1 and rounds_won_a >= rounds_won_b
        ):
            raise RoundsWonTeamWonMismatch

        return (rounds_won_a, rounds_won_b)

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.result.component, discord.ui.RadioGroup)

        # Get the winning team captain ID
        winning_team_captain_id = int(self.result.component.value)

        # Get the rounds won after validation
        rw = self.get_rounds_won(winning_team_captain_id)

        # If validation passes, actually write changes
        await self.r6view.bot.match_manager.set_winning_team(
            interaction.guild_id,
            self.r6view.payload.match_name,
            winning_team_captain_id,
        )
        for team, rounds_won in zip(self.r6view.teams, rw):
            await self.r6view.bot.match_manager.set_team_rounds_won(
                interaction.guild_id,
                self.r6view.payload.match_name,
                team.captain_id,
                rounds_won,
            )

        # Update local MatchEntry instance attached to R6View
        await self.r6view.update_match()

        # Craft and send final result message
        rounds_won_winner, rounds_won_loser = sorted(rw, reverse=True)
        winners = (
            f"The winner of **{self.r6view.payload.match_name}** "
            + f"is **Team {self.r6view.match.winning_team.name}** "
            + f"[{rounds_won_winner} - {rounds_won_loser}]"
        )
        await interaction.response.send_message(winners)
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        ephemeral = True

        if isinstance(error, RoundsWonTeamWonMismatch):
            msg = Canned.ERR_R6DRAFT_ROUNDS_WON_MISMATCH
        elif isinstance(error, ValueError):
            msg = Canned.ERR_R6DRAFT_ROUNDS_WON_TYPE
        else:
            self.r6view.bot.logger.error(
                f"An exception occurred when trying to report match results: {error}"
            )
            traceback.print_exception(type(error), error, error.__traceback__)
            msg = Canned.ERR_R6DRAFT_GEN_RES
            ephemeral = False

        await interaction.response.send_message(msg, ephemeral=ephemeral)
        self.is_valid = False
        self.stop()
