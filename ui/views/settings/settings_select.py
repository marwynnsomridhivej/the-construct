from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from base import SettingsBaseView

from .buttons import SettingsSelectButtons

if TYPE_CHECKING:
    from bot import Bot


__all__ = ("SettingsSelectView",)


class SettingsSelectView(SettingsBaseView):
    def __init__(
        self,
        *,
        guild_id: int,
        user_id: int,
        source_interaction: discord.Interaction,
        bot: Bot,
    ):
        super().__init__(
            guild_id=guild_id,
            user_id=user_id,
            source_interaction=source_interaction,
            button_cls=SettingsSelectButtons,
            parent_view=None,
            bot=bot,
        )

    async def get_text_content(self) -> str:
        return "\n".join(
            [
                "## Select Setting",
                "Select the setting category using the buttons below.",
            ]
        )
