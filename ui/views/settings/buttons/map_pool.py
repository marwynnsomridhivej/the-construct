from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from base import SettingsBaseButtons
from canned import Canned
from exceptions import MapPoolAlreadyExists
from ui import (
    ConfirmationModal,
    SettingsMapPoolCreateModal,
    SettingsMapPoolEditModal,
)
from util import ephemeral, titlecase

if TYPE_CHECKING:
    from ..settings_map_pool import SettingsMapPoolView


__all__ = (
    "SettingsMapPoolButtons",
    "SettingsMapPoolSelectRow",
)


class SettingsMapPoolButtons(SettingsBaseButtons):
    def __init__(self, *, view, show_admin_buttons: bool = False):
        super().__init__(view=view, show_admin_buttons=show_admin_buttons)
        self.parent_view: SettingsMapPoolView

        self.init_buttons()

    def init_buttons(self) -> None:
        buttons = []

        # Add create, edit, and delete buttons if admin
        if self.show_admin_buttons:
            create_button = discord.ui.Button(
                label="Create", style=discord.ButtonStyle.blurple
            )
            create_button.callback = self.create_button_callback
            buttons.append(create_button)

            edit_button = discord.ui.Button(
                label="Edit", style=discord.ButtonStyle.blurple
            )
            edit_button.callback = self.edit_button_callback
            buttons.append(edit_button)

            delete_button = discord.ui.Button(
                label="Delete", style=discord.ButtonStyle.blurple
            )
            delete_button.callback = self.delete_button_callback
            buttons.append(delete_button)

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

    async def create_button_callback(self, interaction: discord.Interaction):
        # Check if any map pools can be created
        if not await self.parent_view.bot.settings_manager.can_create_map_pool(
            interaction.guild_id
        ):
            return await interaction.response.send_message(
                Canned.ERR_SETTINGS_MAP_POOL_CAP, **ephemeral()
            )

        # Display create modal and wait until it is finished
        create_modal = SettingsMapPoolCreateModal(self.parent_view.bot)
        await interaction.response.send_modal(create_modal)
        await create_modal.wait()

        # If something went wrong
        if not create_modal.is_valid:
            return

        # Create the custom map pool
        try:
            pool = await self.parent_view.bot.settings_manager.create_map_pool(
                interaction.guild_id,
                interaction.user.id,
                create_modal.name,
                create_modal.maps,
            )
        except MapPoolAlreadyExists:
            return await interaction.followup.send(
                Canned.ERR_SETTINGS_MAP_POOL_NAME_TAKEN, ephemeral=True
            )
        else:
            await interaction.followup.send(
                f'The map pool "{pool.name}" (`{len(pool)}` map{"s" if len(pool) != 1 else ""}) has been created',
                ephemeral=True,
            )

        # Update parent view to reflect changes
        await self.parent_view.update()

    async def edit_button_callback(self, interaction: discord.Interaction):
        # Get selected map pool name from the selector
        name = self.parent_view.get_selected_map_pool_name()
        if not name:
            return await interaction.response.send_message(
                Canned.ERR_SETTINGS_MAP_POOL_MANAGE_NO_NAME, **ephemeral(seconds=10)
            )

        # Edit the specified map pool instance and wait until interaction completes
        pool = await self.parent_view.bot.settings_manager.get_map_pool(
            interaction.guild_id, name
        )
        edit_modal = SettingsMapPoolEditModal(self.parent_view.bot, pool)
        await interaction.response.send_modal(edit_modal)
        await edit_modal.wait()

        # If something went wrong or no changes were made, don't proceed
        if not edit_modal.is_valid:
            return

        # Track changes
        changes = []

        # Rename if a new name was specified
        if pool.name != edit_modal.name:
            try:
                await self.parent_view.bot.settings_manager.name_map_pool(
                    interaction.guild_id,
                    pool.name,
                    edit_modal.name,
                )
                changes.append("name")
            except MapPoolAlreadyExists:
                return await interaction.followup.send(
                    content=Canned.ERR_SETTINGS_MAP_POOL_NAME_TAKEN,
                    ephemeral=True,
                )

        # Update maps if maps list was modified
        if sorted(pool.maps) != sorted(edit_modal.maps):
            await self.parent_view.bot.settings_manager.modify_map_pool_maps(
                interaction.guild_id,
                edit_modal.name,
                edit_modal.maps,
            )
            changes.append("maps")

        # Build text summary for any changes that were processed
        changes_text = "## Changes Made"
        if "name" in changes:
            changes_text += f"\n### Name\n`{pool.name}` → `{edit_modal.name}`"
        if "maps" in changes:
            diff = set(pool.maps).symmetric_difference(edit_modal.maps)
            changes_text += "\n### Maps\n" + "\n".join(
                sorted(
                    [
                        f"[{'+' if r6map in edit_modal.maps else '-'}] {titlecase(r6map.replace('_', ' '))}"
                        for r6map in diff
                    ]
                )
            )

        # Send text summary
        await interaction.followup.send(
            content=changes_text,
            ephemeral=True,
        )

        # Update parent view to reflect changes
        await self.parent_view.update()

    async def delete_button_callback(self, interaction: discord.Interaction):
        # Get selected map pool name from the selector
        name = self.parent_view.get_selected_map_pool_name()
        if not name:
            return await interaction.response.send_message(
                Canned.ERR_SETTINGS_MAP_POOL_MANAGE_NO_NAME, **ephemeral(seconds=10)
            )

        # Send delete modal and wait until interaction completes
        delete_modal = ConfirmationModal(operation="Delete Custom Map Pool")
        await interaction.response.send_modal(delete_modal)
        await delete_modal.wait()

        # Don't proceed if canceled
        if not delete_modal.proceed:
            return

        # Delete specified custom map pool
        await self.parent_view.bot.settings_manager.delete_map_pool(
            interaction.guild_id,
            name,
        )

        # Send confirmation message
        await interaction.followup.send(
            f'The custom map pool "{name}" was successfully deleted',
            ephemeral=True,
        )

        # Update parent view to reflect changes
        await self.parent_view.update()

    async def back_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.parent_view.go_back()

    async def refresh_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.parent_view.update()


class SettingsMapPoolSelectRow(SettingsBaseButtons):
    def __init__(self, *, view, names: list[str]):
        super().__init__(view=view)
        self.parent_view: SettingsMapPoolView

        self.name_select = discord.ui.Select(
            placeholder="Select the custom map pool you wish to edit or delete",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=titlecase(name),
                    value=name,
                )
                for name in names
            ],
        )

        self.name_select.callback = self._select_callback

        self.add_item(self.name_select)

    async def _select_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

    @property
    def value(self) -> str | None:
        return self.name_select.values[0] if self.name_select.values else None
