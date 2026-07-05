from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from util import ephemeral, titlecase

if TYPE_CHECKING:
    from bot import Bot


__all__ = ("QueueDeleteModal",)


class QueueDeleteModal(discord.ui.Modal):
    def __init__(self, bot: Bot, options: list[str]):
        super().__init__(title="Delete Queue")

        self.bot = bot
        self.options = options
        self.is_valid: bool = False

        # Attributes with user input data
        self.queue_name_select: discord.ui.Label
        self.confirmation_name_input: discord.ui.Label

        self.init_components()

    @property
    def queue_name(self) -> str:
        assert isinstance(self.queue_name_select.component, discord.ui.Select)
        return self.queue_name_select.component.values[0].lower()

    @property
    def confirmation_name(self) -> str:
        assert isinstance(self.confirmation_name_input.component, discord.ui.TextInput)
        return self.confirmation_name_input.component.value

    def init_components(self) -> None:
        # Select queue to be deleted
        self.queue_name_select = discord.ui.Label(
            text="Select Queue",
            description="Select the name of the queue you wish to delete",
            component=discord.ui.Select(
                options=[
                    discord.SelectOption(label=titlecase(option), value=titlecase(option))
                    for option in self.options
                ],
                required=True,
            ),
        )

        # Get delete confirmation
        self.confirmation_name_input = discord.ui.Label(
            text="Confirmation",
            description="Enter the name of the selected queue above (case sensitive) to confirm",
            component=discord.ui.TextInput(
                placeholder="Enter the queue name here",
                required=True,
            ),
        )

        for item in [self.queue_name_select, self.confirmation_name_input]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Check if confirmation name and selected queue name match
        assert isinstance(self.queue_name_select.component, discord.ui.Select)
        if self.queue_name_select.component.values[0] != self.confirmation_name:
            raise ValueError

        # Defer interaction response if no error
        await interaction.response.defer()

        # Set is_valid flag to true and stop listening
        self.is_valid = True
        self.stop()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        msg = Canned.ERR_QUEUE_DELETE
        if isinstance(error, ValueError):
            msg = Canned.ERR_QUEUE_DELETE_CONFIRM_NAME_MISMATCH
        else:
            self.bot.logger.error(f"An exception occurred when creating queue: {error}")
            traceback.print_exception(type(error), error, error.__traceback__)

        await interaction.response.send_message(msg, **ephemeral())
        self.stop()
