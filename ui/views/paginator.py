from abc import ABC, abstractmethod

import discord

__all__ = (
    "Paginator",
    "PaginatorButtonRow",
)


class Paginator(discord.ui.LayoutView, ABC):
    def __init__(
        self,
        *,
        source_interaction: discord.Interaction,
        data: dict,
        per_page: int,
        timeout: float | None = None,
    ):
        super().__init__(timeout=timeout)

        # Original interaction, so we can edit ephemeral messages
        self.source_interaction = source_interaction

        self._data = data
        self.current_page = 0

        assert per_page > 0
        self.per_page = per_page
        self.max_pages = (len(self._data) + self.per_page - 1) // self.per_page

        # References for existing components
        self.action_buttons: PaginatorButtonRow | None = None

    @abstractmethod
    def init_components(self) -> None:
        pass

    def can_paginate(self, page: int) -> bool:
        return 0 <= page <= self.max_pages - 1

    async def decrement_page(self) -> None:
        if self.can_paginate(self.current_page - 1):
            self.current_page -= 1
            await self.update_view()

    async def increment_page(self) -> None:
        if self.can_paginate(self.current_page + 1):
            self.current_page += 1
            await self.update_view()

    async def update_view(self) -> None:
        self.clear_items()
        self.init_components()
        await self.source_interaction.edit_original_response(
            view=self, allowed_mentions=discord.AllowedMentions.none()
        )


class PaginatorButtonRow(discord.ui.ActionRow):
    def __init__(self, *, view: Paginator):
        super().__init__()
        self._pview = view

    def init_components(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                match item.label:
                    case "Previous":
                        # If we can paginate, DON'T DISABLE
                        item.disabled = not self._pview.can_paginate(
                            self._pview.current_page - 1
                        )
                    case "Next":
                        # If we can paginate, DON'T DISABLE
                        item.disabled = not self._pview.can_paginate(
                            self._pview.current_page + 1
                        )
                    case _:
                        pass

    @discord.ui.button(label="Previous", emoji="◀️")
    async def _go_previous_page_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._pview.decrement_page()
        await interaction.response.defer()

    @discord.ui.button(label="Next", emoji="▶️")
    async def _go_next_page_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self._pview.increment_page()
        await interaction.response.defer()
