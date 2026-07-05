from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from matchmanager import R6_MAX_PLAYERS_PER_TEAM, MatchTeam
from util import titlecase

if TYPE_CHECKING:
    from ...views import R6View

__all__ = ("R6DraftModal",)


class R6DraftModal(discord.ui.Modal):
    def __init__(self, *, view: R6View, other_team: MatchTeam):
        super().__init__(title="Draft Player")
        self.r6view = view
        self.other_team = other_team

        for item in self.init_components():
            self.add_item(item)

    @property
    def can_show_finalised_button(self) -> bool:
        return (
            R6_MAX_PLAYERS_PER_TEAM - len(self.other_team.players)
            >= len(self.r6view.draftable_players) - 1
        )

    @property
    def team_draft_finalised(self) -> bool:
        assert isinstance(self.mark_final_draft.component, discord.ui.Select)
        return (
            bool(self.mark_final_draft.component.values)
            and self.mark_final_draft.component.values[0] == "yes"
        )

    def init_components(self) -> list[discord.ui.Label]:
        self.draft = discord.ui.Label(
            text="Draft Player",
            description="Select a player to draft",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(label=name, value=_id)
                    for name, _id in self.r6view.draftable_players
                ],
                required=True,
            ),
        )
        self.mark_final_draft = discord.ui.Label(
            text="Finalise Team Draft",
            description="Would you like to give the other team the rest of the players (except for the one you selected)?",
            component=discord.ui.Select(
                options=[
                    discord.SelectOption(
                        label=titlecase(opt), value=opt, default=opt == "no"
                    )
                    for opt in ["yes", "no"]
                ],
                min_values=1,
                max_values=1,
                required=True,
            ),
        )

        items = [self.draft]
        if self.can_show_finalised_button:
            items.append(self.mark_final_draft)

        return items

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.draft.component, discord.ui.RadioGroup)
        assert isinstance(self.mark_final_draft.component, discord.ui.Select)
        assert isinstance(interaction.channel, discord.Thread)
        assert self.draft.component.value is not None
        assert (guild_id := interaction.guild_id) is not None
        assert (other_captain_id := self.other_team.captain_id) is not None

        captain_id = interaction.user.id
        drafted_id = int(self.draft.component.value)
        remaining_player_ids = remaining_player_ids = [
            int(player_id)
            for _, player_id in self.r6view.draftable_players
            if int(player_id) != drafted_id
        ]

        # Use MatchManager.draft to write to disk
        await self.r6view.bot.match_manager.draft_player(
            guild_id, self.r6view.payload.match_name, captain_id, drafted_id
        )

        # If finalise draft is selected, draft all remaining players in the pool to the other team
        if self.team_draft_finalised:
            for player_id in remaining_player_ids:
                await self.r6view.bot.match_manager.draft_player(
                    guild_id,
                    self.r6view.payload.match_name,
                    other_captain_id,
                    player_id,
                )

        # Update local MatchEntry instance attached to R6View
        await self.r6view.update_match()

        # Notify
        msg = [
            f"Captain <@{captain_id}> has drafted <@{drafted_id}>",
        ]

        # If team draft finalised was selected, add to notification
        if self.team_draft_finalised:
            msg.append(
                "\n".join(
                    [
                        f"\n**Captain <@{captain_id}> finalised their team draft early**. The following "
                        + f"players have been drafted captain <@{self.other_team.captain_id}>'s team:",
                        "\n".join([f"- <@{_id}>" for _id in remaining_player_ids]),
                    ]
                )
            )

        # Send draft notificatoin
        await interaction.response.send_message("\n".join(msg), delete_after=10)

        # If team draft finalised, return early (no need to check if players remain in the pool)
        if self.team_draft_finalised:
            return

        # Check if there is one player left. If so, do the following actions:
        # If playercount is:
        #   EVEN    --> auto-draft to opposite side (higher elo captain)
        #   ODD     --> auto-draft to same side (lower elo captain)
        #
        # If there is more than one player left, notify the other captain they can draft.
        if len(self.r6view.draftable_players) > 1:
            await interaction.channel.send(
                f"*It is now <@{self.r6view.other_captain_id(captain_id)}>'s turn to draft*",
                delete_after=10.0,
            )
            return

        # Last player to draft in draftable [name, id (in string form)]
        drafted_id = int(self.r6view.draftable_players[0][1])

        # Switch captain_id to the other captain if playercount is EVEN
        # Do not switch if playercount is ODD, otherwise higher elo captain is on the team +1
        if self.r6view.playercount % 2 == 0:
            captain_id = self.r6view.other_captain_id(captain_id)

        # Draft the last remaining player
        await self.r6view.bot.match_manager.draft_player(
            guild_id, self.r6view.payload.match_name, captain_id, drafted_id
        )

        # Update local MatchEntry instnace attached to R6View
        await self.r6view.update_match()

        # Notify
        await interaction.channel.send(
            f"Captain <@{captain_id}> has drafted <@{drafted_id}>", delete_after=10.0
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.r6view.bot.logger.error(
            f"An exception occurred when trying to draft player: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_R6DRAFT_GEN_DRAFT)
