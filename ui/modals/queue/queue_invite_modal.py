from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from util import ephemeral, titlecase

if TYPE_CHECKING:
    from bot import Bot


__all__ = ("QueueInviteModal",)


class QueueInviteModal(discord.ui.Modal):
    def __init__(self, bot: Bot, invitable_queues: list[str]):
        super().__init__(title="Invite Players")

        self.bot = bot
        self.invitable_queues = invitable_queues
        self.is_valid: bool = False

        # Attributes with user input data
        self.queue_name_select: discord.ui.Label
        self.invite_user_select: discord.ui.Label

        self.init_components()

    @property
    def queue_name(self) -> str:
        assert isinstance(self.queue_name_select.component, discord.ui.Select)
        return self.queue_name_select.component.values[0]

    @property
    def invited_users(self) -> list[discord.User | discord.Member]:
        assert isinstance(self.invite_user_select.component, discord.ui.UserSelect)
        return self.invite_user_select.component.values

    def init_components(self) -> None:
        # Get name of queue to invite users to
        self.queue_name_select = discord.ui.Label(
            text="Select Queue",
            description="Which queue should the players be invited to?",
            component=discord.ui.Select(
                options=[
                    discord.SelectOption(
                        label=titlecase(name),
                        value=name,
                    )
                    for name in self.invitable_queues
                ],
                min_values=1,
                max_values=1,
                required=True,
            ),
        )

        # Get users to invite
        self.invite_user_select = discord.ui.Label(
            text="Select Players",
            description="Select the players you wish to invite to join the queue",
            component=discord.ui.UserSelect(
                min_values=1,
                max_values=10,
                required=True,
            ),
        )

        for item in [self.queue_name_select, self.invite_user_select]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Immediately defer interaction response
        await interaction.response.defer()

        # Check if any bots were selected
        for user in self.invited_users:
            if user.bot:
                raise ValueError

        # Set is_valid flag to true when no bots are detected
        self.is_valid = True
        self.stop()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        if isinstance(error, ValueError):
            await interaction.response.send_message(Canned.ERR_BOT_USER, **ephemeral())
        else:
            self.bot.logger.error(
                f"An exception occurred while selecting players to invite: {error}"
            )
            traceback.print_exception(type(error), error, error.__traceback__)
            await interaction.response.send_message(
                Canned.ERR_QUEUE_INVITE, **ephemeral()
            )

        self.stop()
