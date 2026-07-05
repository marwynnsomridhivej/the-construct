from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from util import ephemeral, titlecase

if TYPE_CHECKING:
    from bot import Bot

__all__ = ("QueueLockModal",)


class QueueLockModal(discord.ui.Modal):
    def __init__(self, bot: Bot, lockable_queues: list[str]):
        super().__init__(title="Lock Queue")

        self.bot = bot
        self.lockable_queues = lockable_queues
        self.is_valid: bool = False

        # Attributes with user input data
        self.queue_lock_select: discord.ui.Label

        self.init_components()

    @property
    def selected_queue_names(self) -> list[str]:
        assert isinstance(self.queue_lock_select.component, discord.ui.Select)
        return self.queue_lock_select.component.values

    def init_components(self) -> None:
        # Get queues to lock
        self.queue_lock_select = discord.ui.Label(
            text="Select Queues",
            description="Select the name of any queues you wish to lock",
            component=discord.ui.Select(
                options=[
                    discord.SelectOption(label=titlecase(name), value=name.lower())
                    for name in self.lockable_queues
                ],
                placeholder="Please select at least one queue",
                min_values=1,
                max_values=len(self.lockable_queues),
                required=True,
            ),
        )

        self.add_item(self.queue_lock_select)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Immediately defer interaction response
        await interaction.response.defer()

        # Set is_valid flag to true and stop listening
        self.is_valid = True
        self.stop()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        self.bot.logger.error(f"An exception occurred when locking queue: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        await interaction.response.send_message(Canned.ERR_QUEUE_LOCK, **ephemeral())
        self.stop()
