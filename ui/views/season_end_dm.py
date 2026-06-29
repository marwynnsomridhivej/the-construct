import discord

from queuemanager import QueueType
from statsmanager import StatsPlayer, StatsSeason
from util import ICON

__all__ = ("SeasonEndDMView",)


class SeasonEndDMView(discord.ui.LayoutView):
    def __init__(
        self, *, guild: discord.Guild, season: StatsSeason, data: dict[QueueType, dict]
    ):
        super().__init__(timeout=None)

        self._guild = guild
        self._season = season
        self._data = data

        self.init_components()

    def _get_rating_text(self, player: StatsPlayer) -> str:
        # Refer to appropriate rating metrics
        _current, _max = (
            (player.rating, player.max_rating)
            if not player.is_legacy
            else (player.points, player.max_points)
        )
        _type = "Rating" if not player.is_legacy else "Points"

        # Return final formatted string
        return f"- {_type}: `{_current}` `({_max} peak)`"

    @property
    def text_display(self) -> list[discord.ui.Item]:
        items = []

        # Header
        header = discord.ui.TextDisplay(
            "\n".join(
                [
                    f"## End of Season Summary - {self._season.name.title()}",
                    f"The administrators for *{self._guild.name}* have ended the "
                    + "current season. Here is a recap on your performance and server rank.",
                ]
            )
        )
        items.append(header)
        items.append(discord.ui.Separator())

        for queue_type, data in self._data.items():
            rank: int = data["rank"]
            player: StatsPlayer = data["player"]
            items.append(
                discord.ui.TextDisplay(
                    "\n".join(
                        [
                            f"### {queue_type}",
                            f"- Server rank: `{rank}`/`{self._season.get_data_by_queue_type(queue_type).player_count}`",
                            f"- Matches Played: `{player.matches_played}`",
                            self._get_rating_text(player),
                            f"- Wins: `{player.wins}`",
                            f"- Losses: `{player.losses}`",
                            f"- Winrate (W/L ratio): `{player.wl_ratio * 100}%`",
                            f"- Times MVP: `{player.times_mvp}`",
                        ]
                    )
                )
            )
            items.append(discord.ui.Separator())

        # Ranking footer disclaimer
        disclaimer = discord.ui.TextDisplay(
            "-# The end of season summary only displays final standings for queue types you have played "
            + "at least one game in (and have thus obtained a ranking). Multiple people can have the same "
            + "rank if they have the same rating or amount of points"
        )
        items.append(disclaimer)

        return items

    def init_components(self) -> None:
        container = discord.ui.Container(
            discord.ui.Section(
                *self.text_display[:1],
                accessory=discord.ui.Thumbnail(
                    self._guild.icon.url if self._guild.icon is not None else ICON
                ),
            ),
            *self.text_display[1:],
            accent_color=discord.Color.blurple(),
        )
        self.add_item(container)
