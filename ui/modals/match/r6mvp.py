from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, List

import discord

from canned import Canned
from exceptions import MVPAlreadyAssigned
from util import ephemeral

if TYPE_CHECKING:
    from ...views import R6View

__all__ = ("R6MVPModal",)


class R6MVPModal(discord.ui.Modal):
    def __init__(self, *, view, captain_id: int = None):
        super().__init__(title="Designate MVP")
        self._r6view: R6View = view

        for item in self._init_components(captain_id):
            self.add_item(item)

    def _init_components(self, captain_id: int) -> List[discord.ui.Item]:
        # Assemble a list of players that are on the team of the specified captain id
        players: List[discord.Member] = [
            self._r6view.bot.get_guild(self._r6view.payload.guild_id).get_member(
                player_id
            )
            for player_id in self._r6view.match.get_team_of_user(captain_id).players
        ]

        self.mvp_select = discord.ui.Label(
            text="Designate Team MVP",
            description="Select the member on your team that contributed the most to the team",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(label=p.display_name, value=str(p.id))
                    for p in players
                ],
                required=True,
            ),
        )
        return [self.mvp_select]

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.mvp_select.component, discord.ui.RadioGroup)

        captain_id = interaction.user.id
        mvp_id = int(self.mvp_select.component.value)

        try:
            await self._r6view.bot.match_manager.designate_mvp(
                interaction.guild_id,
                self._r6view.payload.match_name,
                mvp_id,
            )
        except MVPAlreadyAssigned:
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_MVP_EXISTS, **ephemeral()
            )

        # Update local MatchEntry instance attached to R6View
        await self._r6view.update_match()

        await interaction.response.send_message(
            f"Captain <@{captain_id}> has designated <@{mvp_id}> as the team's MVP",
            delete_after=10.0,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self._r6view.bot.logger.error(
            f"An exception occurred when trying to designate MVP: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_R6DRAFT_GEN_MVP)
