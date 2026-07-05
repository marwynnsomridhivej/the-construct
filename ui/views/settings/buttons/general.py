from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from base import SettingsBaseButtons
from ui import SettingsBindTextChannelModal, SettingsSetAdminModal

if TYPE_CHECKING:
    from ..settings_general import SettingsGeneralView

__all__ = ("SettingsGeneralButtons",)


class SettingsGeneralButtons(SettingsBaseButtons):
    def __init__(self, *, view: SettingsGeneralView, show_admin_buttons: bool = False):
        super().__init__(view=view, show_admin_buttons=show_admin_buttons)

        self.init_buttons()

    def init_buttons(self) -> None:
        buttons = []

        # Add admin buttons if needed
        if self.show_admin_buttons:
            set_admins_button = discord.ui.Button(
                label="Set Admins", style=discord.ButtonStyle.blurple
            )
            set_admins_button.callback = self.set_admins_button_callback
            buttons.append(set_admins_button)

            bind_text_channel_button = discord.ui.Button(
                label="Bind Text Channel", style=discord.ButtonStyle.blurple
            )
            bind_text_channel_button.callback = self.bind_text_channel_button_callback
            buttons.append(bind_text_channel_button)

        # Always show refresh button
        refresh_button = discord.ui.Button(
            label="Refresh", style=discord.ButtonStyle.grey
        )
        refresh_button.callback = self.refresh_button_callback
        buttons.append(refresh_button)

        # Always show back button
        back_button = discord.ui.Button(label="Back", style=discord.ButtonStyle.grey)
        back_button.callback = self.back_button_callback
        buttons.append(back_button)

        for button in buttons:
            self.add_item(button)

    async def set_admins_button_callback(self, interaction: discord.Interaction):
        assert (guild_id := interaction.guild_id) is not None

        # Get a list of currently set admin user IDs
        previous_admins = await self.parent_view.bot.settings_manager.get_admins(
            guild_id
        )

        # Create admin modal and wait until execution is finished
        set_admin_modal = SettingsSetAdminModal(
            self.parent_view.bot,
            previous_admins,
        )
        await interaction.response.send_modal(set_admin_modal)
        await set_admin_modal.wait()

        # If something went wrong or no changes were made, don't proceed
        if not set_admin_modal.is_valid:
            return

        # Set admins
        await self.parent_view.bot.settings_manager.set_admins(
            guild_id,
            set_admin_modal.admins,
        )

        # Update parent view to reflect changes
        await self.parent_view.update()

    async def bind_text_channel_button_callback(self, interaction: discord.Interaction):
        assert (guild_id := interaction.guild_id) is not None

        # Get the currently bound channel
        previous_channel_id = (
            await self.parent_view.bot.settings_manager.get_bound_text_channel_id(
                guild_id
            )
        )

        # Create bind text channel modal and wait until execution is finished
        bind_channel_modal = SettingsBindTextChannelModal(
            self.parent_view.bot,
            previous_channel_id,
        )
        await interaction.response.send_modal(bind_channel_modal)
        await bind_channel_modal.wait()

        # If something went wrong or no changes were made, don't proceed
        if not bind_channel_modal.is_valid:
            return

        # Bind channel
        await self.parent_view.bot.settings_manager.bind_text_channel(
            guild_id,
            bind_channel_modal.channel_id,
        )

        # Update parent view to reflect changes
        await self.parent_view.update()

    async def back_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.parent_view.go_back()

    async def refresh_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.parent_view.update()
