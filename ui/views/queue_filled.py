import discord

from queuemanager import QueueEntry
from util import ICON

__all__ = ("QueueFilledDMView",)


class QueueFilledDMView(discord.ui.LayoutView):
    def __init__(self, *, guild: discord.Guild, name: str, entry):
        super().__init__(timeout=None)

        self._guild = guild
        self._name = name
        self._entry: QueueEntry = entry

        self.init_components()

    @property
    def text_display(self) -> list[discord.ui.Item]:
        items = []

        # Header
        header = discord.ui.TextDisplay("## Alert - Queue Full")
        items.append(header)

        body = discord.ui.TextDisplay(
            "\n".join(
                [
                    "A queue you created has just reached maximum occupancy. Details are as follows:",
                    "### Details",
                    f"- Server: `{self._guild.name}`",
                    f"- Name: `{self._name.title()}`",
                    f"- Created at: <t:{self._entry.created_timestamp}:f>",
                    f"- Queue Type: `{self._entry.type}`",
                    "- Players:",
                    "\n".join([f"  - <@{player}>" for player in self._entry.players]),
                ]
            )
        )
        items.append(body)

        return items

    def init_components(self) -> None:
        container = discord.ui.Container(
            discord.ui.Section(
                *self.text_display,
                accessory=discord.ui.Thumbnail(
                    self._guild.icon.url if self._guild.icon is not None else ICON
                ),
            ),
            accent_color=discord.Color.blurple(),
        )
        self.add_item(container)
