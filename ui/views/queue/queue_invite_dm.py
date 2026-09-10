from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord

from canned import Canned
from event import Event, QueueNotifyPayload
from exceptions import AlreadyInQueue, NotInvited, QueueIsFull, QueueIsLocked
from queuemanager import QueueNotifyAction
from util import ICON, titlecase

if TYPE_CHECKING:
    from bot import Bot


__all__ = ("QueueInviteDMView", "QueueInviteDMViewButtons")


INVITE_VALID_FOR_SECONDS = 60 * 15


class QueueInviteDMViewButtons(discord.ui.ActionRow):
    def __init__(self, *, view: QueueInviteDMView):
        super().__init__()

        self.invite_view = view
        self.bot = view.bot
        self.name = view.name
        self.guild = view.guild

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def _accept_invite_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Automatically defer interaction response
        await interaction.response.defer()

        # Attempt to join the queue
        try:
            joined_queue = await self.bot.queue_manager.join_user_to_queue(
                self.guild.id,
                interaction.user.id,
                self.name,
            )

            # Dispatch queue join event
            self.bot.dispatch(
                Event.QUEUE_MEMBERSHIP_CHANGE,
                QueueNotifyPayload.parse(
                    {
                        "guild": self.guild,
                        "name": self.name,
                        "entry": joined_queue,
                        "action": QueueNotifyAction.JOIN,
                        "user": interaction.user,
                    }
                ),
            )
        except AlreadyInQueue:
            msg = Canned.ERR_QUEUE_ALREADY_IN
        except QueueIsFull:
            msg = Canned.ERR_QUEUE_FULL
        except QueueIsLocked:
            msg = Canned.ERR_QUEUE_LOCKED_JOIN
        except Exception:  # noqa: BLE001
            msg = Canned.ERR_QUEUE_JOIN
        else:
            msg = (
                "You have successfully joined the queue "
                + f"`{self.name}` in the server `{self.guild}`"
            )

        # Send confirmation or error message
        await interaction.followup.send(msg, ephemeral=True)

        # Cleanup
        self.invite_view.stop()
        await self.invite_view.parent_message.delete()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def _decline_invite_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Automatically defer interaction response
        await interaction.response.defer()

        # Attempt to remove user ID from invites list
        try:
            await self.bot.queue_manager.remove_invite(
                self.guild.id,
                interaction.user.id,
                self.name,
            )
        except NotInvited:
            pass

        # Send decline confirmation message
        await interaction.followup.send(
            "You have successfully declined the invite for the queue "
            + f"`{self.name}` in the server `{self.guild.name}`",
            ephemeral=True,
        )

        # Cleanup
        self.invite_view.stop()
        await self.invite_view.parent_message.delete()


class QueueInviteDMView(discord.ui.LayoutView):
    def __init__(self, *, bot: Bot, guild: discord.Guild, name: str):
        super().__init__(timeout=INVITE_VALID_FOR_SECONDS)

        self.bot = bot
        self.guild = guild
        self.name = name

        self.init_components()

        # Will be initialised after message is sent
        self.parent_message: discord.Message
        self.user_id: int

    @property
    def text_display(self) -> list[discord.ui.Item]:
        items = []

        # Header
        header = discord.ui.TextDisplay("## Queue Invitation")
        items.append(header)

        # Body
        body = discord.ui.TextDisplay(
            f"You have been invited to join the queue `{titlecase(self.name)}` "
            + f"in the server `{self.guild.name}`."
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
            QueueInviteDMViewButtons(view=self),
            discord.ui.Separator(),
            discord.ui.TextDisplay(
                "-# *This invite expires "
                + f"<t:{int(datetime.now(tz=UTC).timestamp()) + INVITE_VALID_FOR_SECONDS}:R>*"
            ),
            accent_color=discord.Color.blurple(),
        )
        self.add_item(container)

    async def on_timeout(self) -> None:
        # Delete the message when the view times out
        if self.parent_message:
            await self.parent_message.delete()

        # Attempt to remove user ID from invites list
        try:
            await self.bot.queue_manager.remove_invite(
                self.guild.id,
                self.user_id,
                self.name,
            )
        except NotInvited:
            pass
