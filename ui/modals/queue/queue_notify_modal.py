from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from queuemanager import QueueEntry
from util import ephemeral, titlecase

if TYPE_CHECKING:
    from bot import Bot

__all__ = ("QueueNotifyModal",)


class QueueNotifyModal(discord.ui.Modal):
    def __init__(self, bot: Bot, notifiable_queues: dict[str, QueueEntry]):
        super().__init__(title="Configure Queue Notifications")

        self.bot = bot
        self.notifiable_queues = notifiable_queues
        self.is_valid: bool = False

        # Attributes with user input data
        self.queue_notify_select: discord.ui.Label

        self.init_components()

    @property
    def diff(self) -> list[tuple[str, bool]]:
        assert isinstance(self.queue_notify_select.component, discord.ui.Select)
        diff = []
        for name, entry in self.notifiable_queues.items():
            new_value = name in self.queue_notify_select.component.values
            if entry.notify != new_value:
                diff.append((name, new_value))
        return diff

    def init_components(self) -> None:
        # Get queues to notify
        self.queue_notify_select = discord.ui.Label(
            text="Select Queues",
            description="Select the name of any queues you wish to receive notifications for",
            component=discord.ui.Select(
                options=[
                    discord.SelectOption(
                        label=titlecase(name),
                        value=name.lower(),
                        default=entry.notify,
                    )
                    for (name, entry) in self.notifiable_queues.items()
                ],
                min_values=0,
                max_values=len(self.notifiable_queues),
                required=False,
            ),
        )

        self.add_item(self.queue_notify_select)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Immediately defer interaction response
        await interaction.response.defer()

        # Set is_valid flag to true and stop listening
        self.is_valid = True
        self.stop()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        self.bot.logger.error(
            f"An exception occurred when configuring queue notifications: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)

        await interaction.response.send_message(Canned.ERR_QUEUE_NOTIFY, **ephemeral())
        self.stop()
