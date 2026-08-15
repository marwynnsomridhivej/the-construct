from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from exceptions import MatchPanelStateException
from matchmanager import R6_SIDES, R6Side
from util import SYSTEM_RANDOM, ephemeral, titlecase

if TYPE_CHECKING:
    from ...views import R6View

__all__ = ("R6SideModal",)


class R6SideModal(discord.ui.Modal):
    def __init__(self, *, view):
        super().__init__(title="Starting Side Selection")
        self.r6view: R6View = view

        for item in self.init_components():
            self.add_item(item)

    def init_components(self) -> list[discord.ui.Item]:
        self.side_select = discord.ui.Label(
            text="Starting Side Selection",
            description="Select whether your team would like to attack or defend first",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(label=titlecase(side), value=side.value)
                    for side in R6_SIDES
                ],
                required=True,
            ),
        )
        return [self.side_select]

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.side_select.component, discord.ui.RadioGroup)
        assert interaction.guild_id is not None
        assert self.side_select.component.value is not None

        # Prevent condition where a starting side selection can go through when
        # the match panel is reset
        if not self.r6view.finished_map_bans:
            raise MatchPanelStateException

        captain_id = interaction.user.id
        choice = R6Side(self.side_select.component.value)

        # Pick a random side if the choice was R6Side.RANDOM
        if choice == R6Side.RANDOM:
            choice = SYSTEM_RANDOM.choice([R6Side.ATTACKER, R6Side.DEFENDER])

        # Set starting side according to selection
        await self.r6view.bot.match_manager.select_starting_side(
            interaction.guild_id,
            self.r6view.payload.match_name,
            captain_id,
            choice,
        )

        # Update local MatchEntry instance attached to R6View
        await self.r6view.update_match()

        await interaction.response.send_message(
            f"Captain <@{captain_id}>'s team will start as **{choice.lower()}s**.",
            delete_after=10.0,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, MatchPanelStateException):
            await interaction.response.send_message(
                Canned.ERR_R6DRAFT_GEN_STATE, **ephemeral()
            )
            return

        self.r6view.bot.logger.error(
            f"An exception occurred when trying to select starting side: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_R6DRAFT_GEN_SIDE)
