from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from exceptions import QueueAlreadyExists
from queuemanager import ALL_R6_QUEUE_TYPES, QueueType
from util import ephemeral

if TYPE_CHECKING:
    from bot import Bot

__all__ = ("QueueCreateModal",)


class QueueCreateModal(discord.ui.Modal):
    def __init__(self, bot: Bot):
        super().__init__(title="Create Queue")

        self.bot = bot
        self.is_valid: bool = False

        # Attributes with user input data
        self.queue_name_input: discord.ui.Label
        self.queue_type_select: discord.ui.Label

        self.init_components()

    @property
    def queue_name(self) -> str:
        assert isinstance(self.queue_name_input.component, discord.ui.TextInput)
        return self.queue_name_input.component.value.lower()

    @property
    def queue_type(self) -> QueueType:
        assert isinstance(self.queue_type_select.component, discord.ui.Select)
        return QueueType(self.queue_type_select.component.values[0])

    def init_components(self) -> None:
        # Get queue name
        self.queue_name_input = discord.ui.Label(
            text="Queue Name",
            description="Enter the name you would like to use for the queue (up to 100 characters)",
            component=discord.ui.TextInput(
                style=discord.TextStyle.short,
                placeholder="Enter the name here",
                min_length=1,
                max_length=100,
                required=True,
            ),
        )

        # Get queue type
        self.queue_type_select = discord.ui.Label(
            text="Queue Type",
            description="Select the queue type for your queue",
            component=discord.ui.Select(
                options=[
                    discord.SelectOption(
                        label=queue_type.title(),
                        value=queue_type,
                        default=queue_type == QueueType.R6_5V5,
                    )
                    for queue_type in ALL_R6_QUEUE_TYPES
                ],
                required=True,
            ),
        )

        for item in [self.queue_name_input, self.queue_type_select]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Immediately defer interaction response
        await interaction.response.defer()

        # Set is_valid flag to true and stop listening
        self.is_valid = True
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        self.bot.logger.error(f"An exception occurred when creating queue: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        msg = Canned.ERR_QUEUE_CREATE
        if isinstance(error, QueueAlreadyExists):
            msg = Canned.ERR_QUEUE_EXISTS

        await interaction.response.send_message(msg, **ephemeral())
        self.stop()
