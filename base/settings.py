from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import discord

from util import ICON

if TYPE_CHECKING:
    from bot import Bot

__all__ = (
    "SettingsBaseView",
    "SettingsBaseButtons",
)


class SettingsBaseView(discord.ui.LayoutView, ABC):
    def __init__(
        self,
        *,
        guild_id: int,
        user_id: int,
        source_interaction: discord.Interaction,
        button_cls: type["SettingsBaseButtons"],
        parent_view: discord.ui.LayoutView | None,
        bot,
    ):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.user_id = user_id
        self.source_interaction = source_interaction
        self.button_cls = button_cls
        self.parent_view = parent_view
        self.bot: Bot = bot

        # Will be changed in init_components
        self.main_buttons = None
        self.container_id: int | None = None
        self.is_guild_owner: bool = False
        self.is_bot_admin: bool = False

    async def init_components(self) -> None:
        # Prep section with text and thumbnail
        guild = self.bot.get_guild(self.guild_id)
        guild_icon = guild.icon if guild is not None else None
        section = discord.ui.Section(
            discord.ui.TextDisplay(await self.get_text_content()),
            accessory=discord.ui.Thumbnail(
                media=guild_icon.url if guild_icon is not None else ICON,
            ),
        )

        # Add section to container
        container = discord.ui.Container(
            section,
            accent_color=discord.Color.blurple(),
            id=67,
        )
        assert isinstance(container.id, int)
        self.container_id = container.id

        # Show admin message if user is server owner or bot admin
        guild = self.bot.get_guild(self.guild_id)
        self.is_guild_owner = guild is not None and guild.owner_id == self.user_id
        self.is_bot_admin = await self.bot.settings_manager.is_admin(
            self.guild_id, self.user_id
        )
        admin_check = self.is_guild_owner or self.is_bot_admin
        if admin_check:
            admin_message = f"-# *As {'the server owner' if self.is_guild_owner else 'a bot administrator'}, you may modify settings using the buttons below*"
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.TextDisplay(admin_message))

        # Show admin/navigation buttons
        self.main_buttons = self.button_cls(view=self, show_admin_buttons=admin_check)
        container.add_item(self.main_buttons)

        # Add fully built container to view
        self.add_item(container)

    @abstractmethod
    async def get_text_content(self) -> str:
        raise NotImplementedError

    async def update(self) -> None:
        self.clear_items()
        await self.init_components()
        await self.source_interaction.edit_original_response(
            view=self,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def go_back(self):
        await self.source_interaction.edit_original_response(
            view=self.parent_view,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class SettingsBaseButtons(discord.ui.ActionRow, ABC):
    def __init__(self, *, view: SettingsBaseView, show_admin_buttons: bool = False):
        super().__init__()

        self.parent_view = view
        self.show_admin_buttons = show_admin_buttons
