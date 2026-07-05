from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from base import SettingsBaseButtons
from settingsmanager import SettingsChoice
from util import titlecase

from ..settings_general import SettingsGeneralView
from ..settings_map_pool import SettingsMapPoolView

if TYPE_CHECKING:
    from ..settings_select import SettingsSelectView

__all__ = ("SettingsSelectButtons",)


class SettingsSelectButtons(SettingsBaseButtons):
    def __init__(self, *, view, **kwargs):
        super().__init__(view=view, **kwargs)
        self.parent_view: SettingsSelectView

    @discord.ui.button(
        label=titlecase(SettingsChoice.GENERAL), style=discord.ButtonStyle.blurple
    )
    async def _select_general(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Mark interaction as deferred so buttons immediately become available
        await interaction.response.defer()

        view = SettingsGeneralView(
            guild_id=self.parent_view.guild_id,
            user_id=self.parent_view.user_id,
            source_interaction=self.parent_view.source_interaction,
            parent_view=self.parent_view,
            bot=self.parent_view.bot,
        )
        await view.init_components()

        await self.parent_view.source_interaction.edit_original_response(
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @discord.ui.button(
        label=titlecase(SettingsChoice.MAP_POOL), style=discord.ButtonStyle.blurple
    )
    async def _select_map_pool(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Mark interaction as deferred so buttons immediately become available
        await interaction.response.defer()

        view = SettingsMapPoolView(
            guild_id=self.parent_view.guild_id,
            user_id=self.parent_view.user_id,
            source_interaction=self.parent_view.source_interaction,
            parent_view=self.parent_view,
            bot=self.parent_view.bot,
        )
        await view.init_components()

        await self.parent_view.source_interaction.edit_original_response(
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
