from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from matchmanager import R6Side
from util import titlecase

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
                    for side in [R6Side.ATTACKER, R6Side.DEFENDER]
                ],
                required=True,
            ),
        )
        return [self.side_select]

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.side_select.component, discord.ui.RadioGroup)
        assert (guild_id := interaction.guild_id) is not None
        assert self.side_select.component.value is not None

        captain_id = interaction.user.id
        choice = self.side_select.component.value

        # Set starting side according to selection
        await self.r6view.bot.match_manager.select_starting_side(
            guild_id,
            self.r6view.payload.match_name,
            captain_id,
            R6Side(choice),
        )

        # Update local MatchEntry instance attached to R6View
        await self.r6view.update_match()

        await interaction.response.send_message(
            f"Captain <@{captain_id}>'s team will start as **{choice.lower()}s**.",
            delete_after=10.0,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.r6view.bot.logger.error(
            f"An exception occurred when trying to select starting side: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_R6DRAFT_GEN_SIDE)
