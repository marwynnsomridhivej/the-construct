from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from exceptions import MVPAlreadyAssigned
from util import ephemeral

if TYPE_CHECKING:
    from ...views import R6View

__all__ = ("R6MVPModal",)


class R6MVPModal(discord.ui.Modal):
    def __init__(self, *, view: R6View, captain_id: int):
        super().__init__(title="Designate MVP")
        self.r6view = view

        for item in self.init_components(captain_id):
            self.add_item(item)

    def init_components(self, captain_id: int) -> list[discord.ui.Item]:
        # Assemble a list of players that are on the team of the specified captain id
        guild = self.r6view.bot.get_guild(self.r6view.payload.guild_id)
        assert guild is not None

        players: list[discord.Member] = [
            member
            for player_id in self.r6view.match.get_team_of_user(captain_id).players
            if (member := guild.get_member(player_id)) is not None
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
        assert self.mvp_select.component.value is not None
        assert interaction.guild_id is not None

        captain_id = interaction.user.id
        mvp_id = int(self.mvp_select.component.value)

        try:
            await self.r6view.bot.match_manager.designate_mvp(
                interaction.guild_id,
                self.r6view.payload.match_name,
                mvp_id,
            )
        except MVPAlreadyAssigned:
            await interaction.response.send_message(
                Canned.ERR_R6DRAFT_MVP_EXISTS, **ephemeral()
            )
            return

        # Update local MatchEntry instance attached to R6View
        await self.r6view.update_match()

        await interaction.response.send_message(
            f"Captain <@{captain_id}> has designated <@{mvp_id}> as the team's MVP",
            delete_after=10.0,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.r6view.bot.logger.error(
            f"An exception occurred when trying to designate MVP: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_R6DRAFT_GEN_MVP)
