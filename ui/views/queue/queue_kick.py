from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from canned import Canned
from event import Event, QueueNotifyPayload
from exceptions import NotInQueue, QueueIsLocked, QueueProgressStateError
from queuemanager import QueueEntry, QueueNotifyAction
from util import ICON, titlecase

if TYPE_CHECKING:
    from bot import Bot


__all__ = (
    "QueueKickView",
    "QueueKickViewButtons",
)


class QueueKickView(discord.ui.LayoutView):
    def __init__(
        self,
        bot: Bot,
        *,
        guild: discord.Guild,
        queues: dict[str, QueueEntry],
        original_interaction: discord.Interaction,
    ):
        super().__init__(timeout=None)

        self.bot = bot
        self.guild = guild
        self.queues = queues
        self.original_interaction = original_interaction

        # Component attributes
        self.queue_select: discord.ui.Select
        self.player_select: discord.ui.Select

        # Button actionrow
        self.buttons: QueueKickViewButtons

        # Important properties
        self.selected_queue_name: str | None = None

    @property
    def selected_player_ids(self) -> list[int]:
        if not (self.player_select and self.player_select.values):
            return []

        return [int(user_id) for user_id in self.player_select.values]

    def init_components(self, buttons: QueueKickViewButtons) -> None:
        # Initialise self.buttons
        self.buttons = buttons

        # Initialise blank item lists
        items = []

        # Select queue
        self.queue_select = discord.ui.Select(
            options=[
                discord.SelectOption(
                    label=titlecase(name),
                    value=name,
                    default=self.selected_queue_name is not None
                    and name == self.selected_queue_name,
                )
                for name in self.queues
            ],
            min_values=1,
            max_values=1,
            required=True,
        )
        items.append(
            self.generate_label(
                title="Select Queue",
                description="What queue would you like to kick users from?",
                component=self.queue_select,
            )
        )

        # Attach callback so list of players can be updated upon selecting a queue
        self.queue_select.callback = self._queue_select_callback

        # Show the rest of the view if a queue has been selected
        if self.selected_queue_name:
            # Get all players in selected queue
            selected_queue = self.queues[self.selected_queue_name]
            players = [
                member
                for user_id in selected_queue.players
                if (member := self.guild.get_member(user_id)) is not None
            ]

            # User select
            self.player_select = discord.ui.Select(
                options=[
                    discord.SelectOption(
                        label=player.display_name,
                        value=str(player.id),
                    )
                    for player in sorted(
                        players,
                        key=lambda m: m.name,
                    )
                ],
                min_values=0,
                max_values=len(players),
                required=False,
            )
            items.append(
                self.generate_label(
                    title="Select Players",
                    description="Which players would you like to kick?",
                    component=self.player_select,
                )
            )

            # Attach generic callback
            self.player_select.callback = self._player_select_callback

        # Generate the enclosing section and container and add it to the view
        container = self.generate_container(items, buttons=buttons)
        self.add_item(container)

    def set_results_components(self, *, success: list[int], fail: list[int]) -> None:
        # Clear all items
        self.clear_items()

        # Construct summary
        msg = [
            "### Queue Kick Summary\n"
            + f"The results of the kick operation on the queue `{self.selected_queue_name}` is as follows:"
        ]

        # Add successful kicks
        if success:
            msg.append(
                "### Successfully Kicked\n"
                + "\n".join([f"- <@{user_id}>" for user_id in success])
            )

        # Add failed kicks
        if fail:
            msg.append(
                "### Unable to Kick\n"
                + "\n".join([f"- <@{user_id}>" for user_id in fail])
            )

        # If no success or fail, tell user that nothing changed
        if not (success or fail):
            msg.append(Canned.QUEUE_KICK_NO_SPEC)

        # Generate the enclosing section and container and add it to the view
        container = self.generate_container(
            [(discord.ui.TextDisplay("\n".join(msg)), None)]
        )
        self.add_item(container)

    def set_cancel_components(self) -> None:
        # Clear all items
        self.clear_items()

        # Construct container and cancellation message
        container = self.generate_container(
            [
                self.generate_label(
                    title="Kick Canceled",
                    description="No changes have been made",
                    component=None,
                )
            ]
        )
        self.add_item(container)

    def generate_label(
        self, *, title: str, description: str, component: discord.ui.Item | None
    ) -> tuple[discord.ui.TextDisplay, discord.ui.Item | None]:
        return (
            discord.ui.TextDisplay(
                "\n".join(
                    [
                        f"### {title}",
                        description,
                    ]
                )
            ),
            component,
        )

    def generate_container(
        self,
        items: list[tuple[discord.ui.TextDisplay, discord.ui.Item | None]],
        buttons: QueueKickViewButtons | None = None,
    ) -> discord.ui.Container:
        # Wrap selects in a section
        section = discord.ui.Section(
            discord.ui.TextDisplay("## Queue Kick"),
            discord.ui.TextDisplay(
                "The interactive queue kick panel allows queue owners and "
                + "bot administrators to manage player membership in any"
                + "queues they are allowed to administer."
            ),
            accessory=discord.ui.Thumbnail(
                self.guild.icon.url if self.guild.icon else ICON
            ),
        )

        # Create wrapping container
        container = discord.ui.Container(section, accent_color=discord.Color.blurple())

        # Wrap select components in an ActionRow
        for text_display, component in items:
            container.add_item(text_display)
            if component is not None:
                container.add_item(discord.ui.ActionRow(component))

        # Add buttons if provided
        if buttons:
            container.add_item(buttons)

        # Return fully built container
        return container

    async def _queue_select_callback(self, interaction: discord.Interaction) -> None:
        # Immediately defer interaction response
        await interaction.response.defer()

        if not self.queue_select.values:
            return

        # Set selected queue name
        self.selected_queue_name = self.queue_select.values[0]

        # Clear items and reinitialise
        self.clear_items()
        self.init_components(buttons=self.buttons)

        # Send updated view
        await self.original_interaction.edit_original_response(view=self)

    async def _player_select_callback(self, interaction: discord.Interaction) -> None:
        # Immediately defer interaction response
        await interaction.response.defer()


class QueueKickViewButtons(discord.ui.ActionRow):
    def __init__(
        self, *, view: QueueKickView, original_interaction: discord.Interaction
    ):
        super().__init__()
        self.parent_view = view
        self.original_interaction = original_interaction

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.red)
    async def _kick_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Immediately defer interaction response
        await interaction.response.defer()

        # The kick button only appears when a queue is selected
        assert self.parent_view.selected_queue_name

        # Initialise success and fail counters
        success: list[int] = []
        fail: list[int] = []

        # Attempt to kick selected users
        left_queue = None
        for user_id in self.parent_view.selected_player_ids:
            try:
                left_queue = (
                    await self.parent_view.bot.queue_manager.leave_user_from_queue(
                        self.parent_view.guild.id,
                        user_id,
                        self.parent_view.selected_queue_name,
                    )
                )
            except (NotInQueue, QueueProgressStateError, QueueIsLocked):
                fail.append(user_id)
            else:
                success.append(user_id)

        if success:
            # Craft data payload
            payload = QueueNotifyPayload.parse(
                {
                    "guild": self.parent_view.guild,
                    "name": self.parent_view.selected_queue_name,
                    "entry": left_queue,
                    "action": QueueNotifyAction.LEAVE,
                    "user": [
                        user
                        for user_id in success
                        if (user := self.parent_view.bot.get_user(user_id))
                    ],
                }
            )

            # Dispatch queue leave event in bulk
            self.parent_view.bot.dispatch(
                Event.QUEUE_MEMBERSHIP_CHANGE,
                payload,
            )

            # Dispatch queue kick event
            self.parent_view.bot.dispatch(
                Event.QUEUE_KICKED,
                payload,
            )

        # Edit view to display summary and edit original view in the message
        self.parent_view.set_results_components(success=success, fail=fail)
        self.parent_view.stop()
        await self.original_interaction.edit_original_response(view=self.parent_view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def _cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Immediately defer interaction response
        await interaction.response.defer()

        # Send cancellation message
        self.parent_view.set_cancel_components()
        self.parent_view.stop()
        await self.original_interaction.edit_original_response(view=self.parent_view)
