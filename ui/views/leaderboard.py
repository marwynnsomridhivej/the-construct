from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import discord

from .paginator import Paginator, PaginatorButtonRow

if TYPE_CHECKING:
    from queuemanager import QueueType
    from statsmanager import StatsPlayer, StatsSeason

__all__ = ("LeaderboardView",)


class LeaderboardView(Paginator):
    def __init__(
        self, *, source_interaction: discord.Interaction, queue_type, season, rankings
    ):
        super().__init__(
            source_interaction=source_interaction,
            data=rankings,
            per_page=8,
        )

        self._season: StatsSeason = season
        self._data: list[tuple[int, StatsPlayer]] = rankings
        self.queue_type: QueueType = queue_type
        self.created_time = f"<t:{int(datetime.now().timestamp()) if self._season.is_current else self._season.end_timestamp}:f>"

    def _get_rating_text(self, player: StatsPlayer) -> str:
        # Refer to appropriate rating metrics
        _current, _max = (
            (player.rating, player.max_rating)
            if not player.is_legacy
            else (player.points, player.max_points)
        )
        _type = " rating" if not player.is_legacy else "pts"

        # Return final formatted string
        return f"> - `{_current}`{_type} (`{_max}` peak)"

    def paginate_text_display(self) -> list[discord.ui.Item]:
        items = []
        index_base = self.per_page * self.current_page

        for index in range(index_base, index_base + self.per_page):
            try:
                rank, player = self._data[index]
                items.append(
                    discord.ui.TextDisplay(
                        "\n".join(
                            [
                                f"### {rank}. <@{player.id}>",
                                self._get_rating_text(player),
                                f"> - `{player.matches_played}` Match{'es' if player.matches_played != 1 else ''} Played",
                                f"> - `{player.wins}`W/`{player.losses}`L (`{player.wl_ratio * 100}%` W/L)",
                                f"> - `{player.times_mvp}` time{'s' if player.times_mvp != 1 else ''} MVP",
                            ]
                        )
                    )
                )
            except IndexError:
                break
        return items

    def init_components(self) -> None:
        container = discord.ui.Container(
            # Header, name type and page
            discord.ui.TextDisplay(
                "\n".join(
                    [
                        f"## Leaderboard - {self._season.name.title()} [Page {self.current_page + 1}/{self.max_pages}]",
                        f"Queue Type: *{self.queue_type}*",
                    ]
                )
            ),
            discord.ui.Separator(),
            # Actual part that displays leaderboard
            *self.paginate_text_display(),
            discord.ui.Separator(),
            # Tell user when these stats were tabulated and if they are finalised
            discord.ui.TextDisplay(
                f"-# Statistics tabulated {'' if self._season.is_current else 'and finalised '}as of {self.created_time}"
            ),
            # Accent color
            accent_color=discord.Color.blurple(),
        )

        # Don't add navigation buttons unless they are needed
        if len(self._data) > self.per_page:
            if self.action_buttons is None:
                self.action_buttons = PaginatorButtonRow(view=self)
            self.action_buttons.init_components()
            container.add_item(self.action_buttons)

        # Add container to View
        self.add_item(container)
