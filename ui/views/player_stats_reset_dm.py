from typing import List

import discord

from queuemanager import QueueType
from util import ICON

__all__ = ("PlayerStatsResetDMView",)


class PlayerStatsResetDMView(discord.ui.LayoutView):
    def __init__(
        self, *, user: discord.User, guild: discord.Guild, queue_type: QueueType
    ):
        super().__init__(timeout=None)

        self.user = user
        self.guild = guild
        self.queue_type = queue_type

        self.init_components()

    @property
    def text_display(self) -> List[discord.ui.Item]:
        items = []

        # Header
        header = discord.ui.TextDisplay(
            "\n".join(
                [
                    f"## Alert - Stats Reset ({self.queue_type})",
                    f"An administrator for the server `{self.guild.name}` reset your stats for the current active season.",
                ]
            )
        )
        items.append(header)

        # Body
        body = discord.ui.TextDisplay(
            "\n".join(
                [
                    "### How Does This Affect You?",
                    "- Your wins, losses, matches played, and rating have been reset",
                    "- Your placement on the server leaderboard for the current season now reflects this change",
                    "- You are still eligible to participate in matches and can earn points normally",
                    "### Disclaimer",
                    "Although stat resets may be used as a disciplinary measure, having your stats reset is not always "
                    + "an indicator that disciplinary action has been taken against you.",
                ]
            )
        )
        items.append(body)

        return items

    def init_components(self) -> None:
        container = discord.ui.Container(
            discord.ui.Section(
                self.text_display[0],
                accessory=discord.ui.Thumbnail(
                    self.guild.icon.url if self.guild.icon is not None else ICON
                ),
            ),
            self.text_display[1],
            discord.ui.Separator(),
            discord.ui.TextDisplay(
                "-# If you believe this reset was performed in error, please contact server administrators"
            ),
            accent_color=discord.Color.blurple(),
        )
        self.add_item(container)
