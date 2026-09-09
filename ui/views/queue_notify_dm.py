import discord

from event import QueueNotifyPayload
from queuemanager import QueueNotifyAction
from util import ICON, titlecase

__all__ = ("QueueNotifyDMView",)


class QueueNotifyDMView(discord.ui.LayoutView):
    def __init__(
        self,
        *,
        payload: QueueNotifyPayload,
    ):
        super().__init__(timeout=None)

        self.guild = payload.guild
        self.name = payload.name
        self.entry = payload.entry
        self.action = payload.action
        self.user = payload.user

        self.init_components()

    @property
    def text_display(self) -> list[discord.ui.Item]:
        items = []

        # Plurality flag
        is_plural = isinstance(self.user, list) and len(self.user) != 1

        # Header
        header = discord.ui.TextDisplay(
            f"## Player{'s' if is_plural else ''} {titlecase(self.action)} Queue"
        )
        items.append(header)

        # Configure correct player string
        if not isinstance(self.user, list):
            player_string = f"- Player: {self.user.mention} *({self.user.name})*"
        elif len(self.user) != 1:
            player_string = "- Players:\n" + "\n".join(
                [f"  - {user.mention} *({user.name})*" for user in self.user]
            )
        else:
            player_string = f"- Player: {self.user[0].mention} *({self.user[0].name})*"

        body = discord.ui.TextDisplay(
            "\n".join(
                [
                    f"{'Players' if is_plural else 'A player'} just {self.action}"
                    + " your queue. More information is as follows:",
                    "### Details",
                    f"- Server: `{self.guild.name}`",
                    f"- Name: `{titlecase(self.name)}`",
                    player_string,
                    f"- Playercount: `{len(self.entry.players)}/{self.entry.max_players}`",
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
                    self.guild.icon.url if self.guild.icon is not None else ICON
                ),
            ),
            accent_color=discord.Color.green()
            if self.action == QueueNotifyAction.JOIN
            else discord.Color.red(),
        )
        self.add_item(container)
