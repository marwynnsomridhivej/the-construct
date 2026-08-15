from __future__ import annotations

import secrets
import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from exceptions import MatchPanelStateException
from matchmanager import R6Map
from util import ephemeral, titlecase

if TYPE_CHECKING:
    from ...views import R6View

__all__ = ("R6MapBanModal",)


class R6MapBanModal(discord.ui.Modal):
    def __init__(self, *, view: R6View):
        super().__init__(title="Ban Map")
        self.r6view = view

        for item in self.init_components():
            self.add_item(item)

    def init_components(self) -> list[discord.ui.Item]:
        self.map_ban = discord.ui.Label(
            text="Ban Maps",
            description="Select up to two maps to ban. Once submitted, the "
            + "choices cannot be edited.",
            component=discord.ui.CheckboxGroup(
                options=[
                    discord.CheckboxGroupOption(
                        label=titlecase(r6map.replace("_", " ")),
                        value=r6map.value,
                    )
                    for r6map in self.r6view.map_pool
                    if r6map not in self.r6view.match.banned_maps
                ],
                min_values=0,
                max_values=2,
                required=False,
            ),
        )
        return [self.map_ban]

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.map_ban.component, discord.ui.CheckboxGroup)
        assert isinstance(interaction.channel, discord.Thread)
        assert interaction.guild_id is not None

        # Prevent condition where a map ban can go through when the match panel
        # is reset
        if not self.r6view.finished_draft:
            raise MatchPanelStateException

        captain_id = interaction.user.id
        maps_banned = {R6Map(map_name) for map_name in self.map_ban.component.values}

        # Use MatchManager.ban_map to write any banned maps to disk
        if maps_banned:
            await self.r6view.bot.match_manager.ban_maps(
                interaction.guild_id,
                self.r6view.payload.match_name,
                captain_id,
                maps_banned,
            )

        # Add captain ID to list of captains that have submitted map bans
        self.r6view.map_bans_locked_captain_ids.append(captain_id)

        # Notify that the captain has completed map bans
        await interaction.response.send_message(
            f"Captain <@{captain_id}> has completed map bans.", delete_after=10.0
        )

        # Update local MatchEntry instance attached to R6View
        await self.r6view.update_match()

        # Detect if 4 bans were done in total (each side completed their two bans)
        if len(self.r6view.map_bans_locked_captain_ids) == 2:
            maps_remaining = [
                _map
                for _map in self.r6view.map_pool
                if _map not in self.r6view.match.banned_maps
            ]
            await self.r6view.bot.match_manager.select_map(
                interaction.guild_id,
                self.r6view.payload.match_name,
                secrets.choice(maps_remaining),
            )

            # Need to update local MatchEntry instance again
            await self.r6view.update_match()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, MatchPanelStateException):
            await interaction.response.send_message(
                Canned.ERR_R6DRAFT_GEN_STATE, **ephemeral()
            )
            return

        self.r6view.bot.logger.error(
            f"An exception occurred when trying to ban map: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_R6DRAFT_GEN_BAN)
