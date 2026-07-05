from __future__ import annotations

import random
import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from matchmanager import R6Map
from util import titlecase

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
            text="Ban Map",
            description="Select a map to ban",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(
                        label=titlecase(r6map.replace("_", " ")),
                        value=r6map.value,
                    )
                    for r6map in self.r6view.map_pool
                    if r6map not in self.r6view.match.banned_maps
                ],
                required=True,
            ),
        )
        return [self.map_ban]

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.map_ban.component, discord.ui.RadioGroup)
        assert isinstance(interaction.channel, discord.Thread)
        assert (guild_id := interaction.guild_id) is not None

        captain_id = interaction.user.id
        map_banned = R6Map(self.map_ban.component.value)
        map_string = titlecase(map_banned.replace("_", " "))

        # Use MatchManager.ban_map to write to disk
        await self.r6view.bot.match_manager.ban_map(
            guild_id,
            self.r6view.payload.match_name,
            captain_id,
            map_banned,
        )

        # Update local MatchEntry instance attached to R6View
        await self.r6view.update_match()

        # Check if we have banned every map but one and set it to the chosen map
        maps_remaining = [
            _map
            for _map in self.r6view.map_pool
            if _map not in self.r6view.match.banned_maps
        ]

        # Detect if 4 bans were done in total (each side completed their two bans)
        if len(maps_remaining) == len(self.r6view.map_pool) - 4:
            await self.r6view.bot.match_manager.select_map(
                guild_id,
                self.r6view.payload.match_name,
                random.choice(maps_remaining),
            )
            # Need to update local MatchEntry instance again
            await self.r6view.update_match()

        await interaction.response.send_message(
            f"Captain <@{captain_id}> has banned **{map_string}**", delete_after=10.0
        )

        if not self.r6view.finished_map_bans:
            await interaction.channel.send(
                f"*It is now <@{self.r6view.other_captain_id(captain_id)}>'s turn to select a map to ban*",
                delete_after=10.0,
            )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.r6view.bot.logger.error(
            f"An exception occurred when trying to ban map: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_R6DRAFT_GEN_BAN)
