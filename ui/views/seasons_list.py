from __future__ import annotations

from typing import TYPE_CHECKING, List

import discord

from queuemanager import QueueType

from .paginator import Paginator, PaginatorButtonRow

if TYPE_CHECKING:
    from statsmanager import StatsSeason

__all__ = ("SeasonsListView",)


class SeasonsListView(Paginator):
    def __init__(self, *, source_interaction: discord.Interaction, seasons):
        super().__init__(
            source_interaction=source_interaction,
            data=seasons,
            per_page=5,
        )
        self._seasons: List[StatsSeason] = seasons

    def paginate_text_display(self) -> List[discord.ui.Item]:
        items = []
        index_base = self.per_page * self.current_page

        for index in range(index_base, index_base + self.per_page):
            try:
                season = self._seasons[index]
                info_r6_5v5 = season.get_data_by_queue_type(QueueType.R6_5V5)
                info_r6_1v1 = season.get_data_by_queue_type(QueueType.R6_1V1)
                items.append(
                    discord.ui.TextDisplay(
                        "\n".join(
                            [
                                f"### {season.name.title()}{' (Current)' if season.is_current else ''}",
                                f"> - Started: <t:{season.start_timestamp}:f>",
                                f"> - Ended: {f'<t:{season.end_timestamp}:f>' if season.end_timestamp is not None else '`ONGOING`'}",
                                "> - Ranked Players",
                                f">   - 5v5: `{info_r6_5v5.player_count}`",
                                f">   - 1v1: `{info_r6_1v1.player_count}`",
                                "> - Matches Played",
                                f">   - 5v5: `{info_r6_5v5.match_count}`",
                                f">   - 1v1: `{info_r6_1v1.match_count}`",
                            ]
                        )
                    )
                )
                items.append(discord.ui.Separator())
            except IndexError:
                items.pop()
                break
        return items

    def init_components(self) -> None:
        container = discord.ui.Container(
            discord.ui.TextDisplay("## All Seasons"),
            *self.paginate_text_display(),
            accent_color=discord.Color.blurple(),
        )

        if len(self._data) > self.per_page:
            if self.action_buttons is None:
                self.action_buttons = PaginatorButtonRow(view=self)
            self.action_buttons.init_components()
            container.add_item(self.action_buttons)

        self.add_item(container)
