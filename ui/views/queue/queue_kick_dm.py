from __future__ import annotations

import discord

from util import ICON, titlecase

__all__ = ("QueueKickDMView",)


class QueueKickDMView(discord.ui.LayoutView):
    def __init__(self, *, guild: discord.Guild, name: str):
        super().__init__(timeout=0)

        self.guild = guild
        self.name = name

        self.init_components()

    def init_components(self) -> None:
        items = []

        # Header
        header = discord.ui.TextDisplay("## Queue Removal Notification")
        items.append(header)

        # Body
        body = discord.ui.TextDisplay(
            "\n".join(
                [
                    "This automated message is to notify you that you have been removed "
                    + "from a queue. Details are as follows:",
                    f"- Server: `{self.guild.name}`",
                    f"- Queue: `{titlecase(self.name)}`",
                ]
            )
        )
        items.append(body)

        # Footer
        footer = discord.ui.TextDisplay(
            "-# If you believe you were removed from this queue in error, "
            + "please contact a bot administrator in the server"
        )

        # Enclosing section
        section = discord.ui.Section(
            *items,
            accessory=discord.ui.Thumbnail(
                self.guild.icon.url if self.guild.icon else ICON
            ),
        )

        # Enclosing container
        container = discord.ui.Container(
            section,
            discord.ui.Separator(),
            footer,
            accent_color=discord.Color.red(),
        )

        self.add_item(container)
