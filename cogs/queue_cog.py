from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from canned import Canned
from event import Event, QueueFilledPayload, QueueNotifyPayload
from exceptions import (
    AlreadyInQueue,
    AlreadyInvited,
    NoListResults,
    QueueAlreadyExists,
    QueueDoesNotExist,
    QueueIsFull,
    QueueIsLocked,
    QueueLockStateError,
    QueueProgressStateError,
)
from queuemanager import QueueEntry, QueueNotifyAction, QueueOperationResult, QueueType
from ui import (
    QueueCreateModal,
    QueueDeleteModal,
    QueueFilledDMView,
    QueueInviteDMView,
    QueueInviteModal,
    QueueJoinModal,
    QueueKickDMView,
    QueueKickView,
    QueueKickViewButtons,
    QueueLeaveModal,
    QueueListView,
    QueueLockModal,
    QueueNotifyDMView,
    QueueNotifyModal,
    QueueUnlockModal,
)
from util import EventHandlerType, ephemeral, titlecase

if TYPE_CHECKING:
    from bot import Bot


@app_commands.guild_only()
class QueueCog(commands.GroupCog, name="queue"):
    def __init__(self, bot):
        self.bot: Bot = bot

    async def cog_load(self):
        _handlers: dict[EventHandlerType, Event] = {
            self._notify_queue_owner_full: Event.QUEUE_FILLED,
            self._notify_queue_owner_membership: Event.QUEUE_MEMBERSHIP_CHANGE,
            self._notify_queue_kicked_player: Event.QUEUE_KICKED,
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[QueueCog] Successfully loaded")

    async def _notify_queue_owner_membership(self, payload: QueueNotifyPayload) -> None:
        """Send a DM to the queue owner whenever a player joins or leaves
            one of their queues where notifications are enabled.

        Args:
            payload (QueueNotifyPayload): The payload generated upon a player
                joining or leaving the queue.
        """
        # Notify only if notifications are on
        if not payload.entry.notify:
            return

        # Get queue owner
        queue_owner = self.bot.get_user(payload.entry.owner_id)
        if not queue_owner:
            return

        # Attempt to send queue notification
        try:
            await queue_owner.send(
                view=QueueNotifyDMView(payload=payload),
                allowed_mentions=discord.AllowedMentions.none(),
                delete_after=300,
            )
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

    async def _notify_queue_kicked_player(self, payload: QueueNotifyPayload) -> None:
        """Send a DM to the members that were kicked from a queue.

        Args:
            payload (QueueNotifyPayload): The payload generated upon a player
                joining or leaving the queue.
        """
        # Ensure payload.user is a list
        assert isinstance(payload.user, list)

        # Send a DM to each individual user
        for user in payload.user:
            try:
                queue_kicked_dm_view = QueueKickDMView(
                    guild=payload.guild,
                    name=payload.name,
                )
                await user.send(view=queue_kicked_dm_view)
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass

    async def _notify_queue_owner_full(self, payload: QueueFilledPayload) -> None:
        """Send a DM to the queue owner whenever one of their queues
        reaches maximum player capacity.

        Args:
            payload (QueueFilledPayload): The payload generated upon
                a player joining the queue, causing it to become full.
        """
        # Attempt to get user object of queue owner
        user = self.bot.get_user(payload.entry.owner_id)
        if user is None:
            return self.bot.logger.info(
                f"Could not send queue full DM to user {payload.entry.owner_id} (user not found)"
            )

        # Attempt to get guild
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return self.bot.logger.info(
                f"Could not send queue full DM to user {user.id} for guild {payload.guild_id} (guild not found)"
            )

        # If both user and guild are found, send them the QueueFilledDMView
        try:
            await user.send(
                view=QueueFilledDMView(
                    guild=guild,
                    name=payload.name,
                    entry=payload.entry,
                )
            )
        except discord.HTTPException as e:
            self.bot.logger.info(
                f"Unable to send queue filled DM to user {user.id} for guild {guild.id}: {e}"
            )

    @app_commands.command(
        name="create", description="Creates a new queue for a custom match"
    )
    async def _create_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None

        # Check if any queues can be created
        if not await self.bot.queue_manager.can_create_queue(
            guild_id=interaction.guild_id
        ):
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_LIMIT, **ephemeral()
            )

        # Send queue create modal
        queue_create_modal = QueueCreateModal(self.bot)
        await interaction.response.send_modal(queue_create_modal)

        # Wait until interaction has finished
        await queue_create_modal.wait()

        # If an invalid response was received, do not proceed
        if not queue_create_modal.is_valid:
            return

        # Attempt to create the queue
        try:
            await self.bot.queue_manager.create_queue(
                guild_id=interaction.guild_id,
                owner_id=interaction.user.id,
                name=queue_create_modal.queue_name,
                queue_type=queue_create_modal.queue_type,
                notify=queue_create_modal.notify,
            )
        except QueueAlreadyExists:
            return await interaction.followup.send(
                Canned.ERR_QUEUE_EXISTS,
                ephemeral=True,
            )
        else:
            return await interaction.followup.send(
                f"The queue `{titlecase(queue_create_modal.queue_name)} "
                + f"({titlecase(queue_create_modal.queue_type)})` has been created"
            )

    @app_commands.command(
        name="delete", description="Delete a queue you have management permissions on"
    )
    async def _delete_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None

        # Check if any queues can be deleted
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)
        deletable_queues = [
            name
            for name, entry in queues.items()
            if not entry.locked
            and (
                entry.owner_id == interaction.user.id
                or await self.bot.settings_manager.is_admin(
                    interaction.guild_id, interaction.user.id
                )
            )
        ]
        if not deletable_queues:
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_NO_DELETABLE, **ephemeral()
            )

        # Send queue delete modal
        queue_delete_modal = QueueDeleteModal(self.bot, sorted(deletable_queues))
        await interaction.response.send_modal(queue_delete_modal)

        # Wait until interaction has finished
        await queue_delete_modal.wait()

        # If an invalid response was received, do not proceed
        if not queue_delete_modal.is_valid:
            return

        # Attempt to delete the queue
        try:
            await self.bot.queue_manager.delete_queue(
                interaction.guild_id,
                queue_delete_modal.queue_name,
                interaction.user.id,
            )
        except Exception as e:  # noqa: BLE001
            return await interaction.followup.send(
                f"An error has occurred: {e}", ephemeral=True
            )

        return await interaction.followup.send(
            f"The queue `{titlecase(queue_delete_modal.queue_name)}` has been successfully deleted"
        )

    @app_commands.command(name="join", description="Join open queues")
    async def _join_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None
        assert interaction.guild is not None

        # Check if any queues are joinable
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)
        joinable_queues = [
            name.lower()
            for name, entry in queues.items()
            if not entry.locked
            and len(entry.players) < entry.max_players
            and interaction.user.id not in entry.players
        ]
        if not joinable_queues:
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_NO_JOINABLE, **ephemeral()
            )

        # Send queue join modal
        queue_join_modal = QueueJoinModal(self.bot, sorted(joinable_queues))
        await interaction.response.send_modal(queue_join_modal)

        # Wait until interaction has finished
        await queue_join_modal.wait()

        # If an invalid response was received, do not proceed
        if not queue_join_modal.is_valid:
            return

        # Attempt to join all selected queues
        results: list[QueueOperationResult] = []

        for name in queue_join_modal.selected_queue_names:
            msg = None
            joined_queue = None
            try:
                joined_queue = await self.bot.queue_manager.join_user_to_queue(
                    interaction.guild_id,
                    interaction.user.id,
                    name,
                )

                # Dispatch queue join event
                self.bot.dispatch(
                    Event.QUEUE_MEMBERSHIP_CHANGE,
                    QueueNotifyPayload.parse(
                        {
                            "guild": interaction.guild,
                            "name": name,
                            "entry": joined_queue,
                            "action": QueueNotifyAction.JOIN,
                            "user": interaction.user,
                        }
                    ),
                )
            except QueueIsFull:
                msg = Canned.ERR_QUEUE_FULL
            except QueueIsLocked:
                msg = Canned.ERR_QUEUE_LOCKED_JOIN
            except Exception as e:  # noqa: BLE001
                msg = f"An error has occurred: {e}"
            else:
                # If the queue is full after joining, notify queue owner
                if joined_queue.full:
                    self.bot.dispatch(
                        Event.QUEUE_FILLED,
                        QueueFilledPayload(
                            {
                                "guild_id": interaction.guild_id,
                                "name": name,
                                "entry": joined_queue,
                            }
                        ),
                    )
            finally:
                results.append(
                    QueueOperationResult.parse(
                        {
                            "name": titlecase(name),
                            "entry": joined_queue,
                            "success": msg is None and joined_queue is not None,
                            "msg": msg,
                        }
                    )
                )

        # Craft join summary message
        content = [
            "## Queue Join Summary",
            "*The following is a message detailing all queue join attempts "
            + "based on the queues you selected*",
        ]

        # Add any join success names to the summary message
        join_success = [result for result in results if result.success]
        if join_success:
            content.append("### Success")
            content.append(
                "\n".join(
                    [
                        f"- {result.name} - *`{len(result.entry.players)}/{result.entry.max_players}` players*"
                        for result in join_success
                        if result.entry is not None
                    ]
                )
            )

        # Add any join fail names and reason to the summary message
        join_fail = [result for result in results if not result.success]
        if join_fail:
            content.append("### Fail")
            content.append(
                "\n".join(
                    [f"- {result.name} - *`({result.msg})`*" for result in join_fail]
                )
            )

        # Send queue join summary message
        return await interaction.followup.send("\n".join(content), ephemeral=True)

    @app_commands.command(
        name="leave", description="Leave open queues that you are a member of"
    )
    async def _leave_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None
        assert interaction.guild is not None

        # Check if any queues are leaveable
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)
        leaveable_queues = [
            name
            for name, entry in queues.items()
            if not entry.locked and interaction.user.id in entry.players
        ]
        if not leaveable_queues:
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_NO_LEAVEABLE, **ephemeral()
            )

        # Send queue leave modal
        queue_leave_modal = QueueLeaveModal(self.bot, sorted(leaveable_queues))
        await interaction.response.send_modal(queue_leave_modal)

        # Wait until interaction has finished
        await queue_leave_modal.wait()

        # If an invalid response was received, do not proceed
        if not queue_leave_modal.is_valid:
            return

        # Attempt to leave all selected queues
        results: list[QueueOperationResult] = []

        for name in queue_leave_modal.selected_queue_names:
            msg = None
            try:
                left_queue = await self.bot.queue_manager.leave_user_from_queue(
                    interaction.guild_id,
                    interaction.user.id,
                    name,
                )

                # Dispatch queue join event
                self.bot.dispatch(
                    Event.QUEUE_MEMBERSHIP_CHANGE,
                    QueueNotifyPayload.parse(
                        {
                            "guild": interaction.guild,
                            "name": name,
                            "entry": left_queue,
                            "action": QueueNotifyAction.LEAVE,
                            "user": interaction.user,
                        }
                    ),
                )
            except QueueDoesNotExist:
                msg = Canned.ERR_QUEUE_NO_EXISTS
            except QueueIsLocked:
                msg = Canned.ERR_QUEUE_LOCKED_LEAVE
            except Exception as e:  # noqa: BLE001
                msg = f"An error has occurred: {e}"
            finally:
                results.append(
                    QueueOperationResult.parse(
                        {
                            "name": titlecase(name),
                            "success": msg is None,
                            "msg": msg,
                        }
                    )
                )

        # Craft leave summary message
        content = [
            "## Queue Leave Summary",
            "*The following is a message detailing all queue leave attempts "
            + "based on the queues you selected*",
        ]

        # Add any leave success names to the summary message
        leave_success = [result for result in results if result.success]
        if leave_success:
            content.append("### Success")
            content.append("\n".join([f"- {result.name}" for result in leave_success]))

        # Add any leave fail names and reason to the summary message
        leave_fail = [result for result in results if not result.success]
        if leave_fail:
            content.append("### Fail")
            content.append(
                "\n".join(
                    [f"- {result.name} - *`({result.msg})`*" for result in leave_fail]
                )
            )

        # Send queue leave summary message
        return await interaction.followup.send("\n".join(content), ephemeral=True)

    @app_commands.command(name="kick", description="Kick players in an existing queue")
    async def _kick_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None
        assert interaction.guild is not None

        # Check if the user owns any open queues
        is_admin = await self.bot.settings_manager.is_admin(
            interaction.guild_id, interaction.user.id
        )
        queues = await self.bot.queue_manager.get_queues_owned_by(
            interaction.guild_id,
            interaction.user.id,
            admin=is_admin,
        )
        if not queues:
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_OWNERSHIP, **ephemeral()
            )

        # Send ephemeral queue kick view
        queue_kick_view = QueueKickView(
            self.bot,
            guild=interaction.guild,
            queues=queues,
            original_interaction=interaction,
        )
        queue_kick_view.init_components(
            QueueKickViewButtons(
                view=queue_kick_view,
                original_interaction=interaction,
            )
        )
        await interaction.response.send_message(
            view=queue_kick_view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="invite", description="Invite players to join an existing queue"
    )
    async def _invite_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild is not None
        assert interaction.guild_id is not None

        # Check if the user owns any open queues
        is_admin = await self.bot.settings_manager.is_admin(
            interaction.guild_id, interaction.user.id
        )
        queues = await self.bot.queue_manager.get_queues_owned_by(
            interaction.guild_id,
            interaction.user.id,
            admin=is_admin,
        )
        if not queues:
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_OWNERSHIP, **ephemeral()
            )

        # Send queue invite modal
        queue_invite_modal = QueueInviteModal(
            bot=self.bot,
            invitable_queues=sorted([name for name in queues]),
        )
        await interaction.response.send_modal(queue_invite_modal)

        # Wait until interaction has finished
        await queue_invite_modal.wait()

        # If an invalid response was received, do not proceed
        if not queue_invite_modal.is_valid:
            return

        # Typehint assert
        assert isinstance(interaction.channel, (discord.TextChannel, discord.Thread))

        # Attempt to invite selected users for the selected queue
        try:
            (
                invitable,
                non_invitable,
                bot_invite,
            ) = await self.bot.queue_manager.check_can_invite_users_to_queue(
                interaction.guild_id,
                queue_invite_modal.invited_users,
                queue_invite_modal.queue_name,
            )
        except QueueIsFull:
            return await interaction.followup.send(
                Canned.ERR_QUEUE_FULL, ephemeral=True
            )

        # Store successful and failed invites
        success: list[discord.User] = []
        fail: list[tuple[discord.User, str]] = []

        # Attempt to invite invitable users
        for user in invitable:
            # Get length of failed invites list
            prev_length = len(fail)

            # Attempt to add to the invite list first.
            # If this fails, do not proceed
            try:
                await self.bot.queue_manager.add_invite(
                    interaction.guild_id, user.id, queue_invite_modal.queue_name
                )
            except QueueIsLocked:
                fail.append((user, "queue is locked"))
            except AlreadyInQueue:
                fail.append((user, "already in queue"))
            except AlreadyInvited:
                fail.append((user, "already invited"))

            # Do not proceed after an exception was raised
            if len(fail) > prev_length:
                continue

            # Attempt to send the user a DM. If this fails, the invite is
            # to be removed, even if adding it to the database was successful,
            # since it is functionally equivalent of never being invited for
            # the end user
            try:
                invite_dm_view = QueueInviteDMView(
                    bot=self.bot,
                    guild=interaction.guild,
                    name=queue_invite_modal.queue_name,
                )
                msg = await user.send(view=invite_dm_view)
                invite_dm_view.parent_message = msg
                invite_dm_view.user_id = user.id
            except discord.Forbidden:
                fail.append((user, "user blocked DMs"))
            except discord.NotFound:
                fail.append((user, "user was not found"))
            except discord.HTTPException:
                fail.append((user, "could not send DM"))

            # Do not proceed after an exception was raised
            if len(fail) > prev_length:
                await self.bot.queue_manager.remove_invite(
                    interaction.guild_id, user.id, queue_invite_modal.queue_name
                )
                continue

            # Should both steps go without issue, consider it a success
            success.append(user)

        # Add selected bot users to the failed list with reason
        for user in bot_invite:
            fail.append((user, "cannot invite bot users"))

        # Send message confirming all invites have been sent
        msg = []
        if success:
            msg.append(
                "### Invites Sent\nInvites were successfully sent to the following players:\n"
                + "\n".join([f"- {user.mention}" for user in success])
            )
        if non_invitable:
            msg.append(
                "### Could Not Invite\nInvites could not be sent to the following "
                + "players due to them having already joined the queue or have an invite pending:\n"
                + "\n".join([f"- {user.mention}" for user in non_invitable])
            )
        if fail:
            msg.append(
                "### Error\nAn error occurred while sending invites to the following players:\n"
                + "\n".join(
                    [f"- {user.mention} *({reason})*" for (user, reason) in fail]
                )
            )
        return await interaction.followup.send(
            "\n".join(msg),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="lock", description="Lock an existing queue")
    async def _lock_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None

        # Check if any queues are lockable
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)
        is_admin = await self.bot.settings_manager.is_admin(
            interaction.guild_id,
            interaction.user.id,
        )
        lockable_queues = [
            name
            for name, entry in queues.items()
            if not entry.locked and (interaction.user.id == entry.owner_id or is_admin)
        ]
        if not lockable_queues:
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_NO_LOCKABLE, **ephemeral()
            )

        # Send queue lock modal
        queue_lock_modal = QueueLockModal(self.bot, sorted(lockable_queues))
        await interaction.response.send_modal(queue_lock_modal)

        # Wait until interaction has finished
        await queue_lock_modal.wait()

        # If an invalid response was received, do not proceed
        if not queue_lock_modal.is_valid:
            return

        # Attempt to lock all selected queues
        results: list[QueueOperationResult] = []

        for name in queue_lock_modal.selected_queue_names:
            msg = None
            try:
                await self.bot.queue_manager.set_queue_lock_state(
                    interaction.guild_id,
                    interaction.user.id,
                    name,
                    True,
                    admin=is_admin,
                )
            except QueueDoesNotExist:
                msg = Canned.ERR_QUEUE_NO_EXISTS
            except QueueLockStateError:
                msg = Canned.ERR_QUEUE_LOCKSTATE_L
            except QueueProgressStateError:
                msg = Canned.ERR_QUEUE_PROGSTATE
            except Exception as e:  # noqa: BLE001
                msg = f"An error has occurred: {e}"
            finally:
                results.append(
                    QueueOperationResult.parse(
                        {
                            "name": titlecase(name),
                            "success": msg is None,
                            "msg": msg,
                        }
                    )
                )

        # Craft lock summary message
        content = [
            "## Queue Lock Summary",
            "*The following is a message detailing all queue lock attempts "
            + "based on the queues you selected*",
        ]

        # Add any lock success names to the summary message
        lock_success = [result for result in results if result.success]
        if lock_success:
            content.append("### Success")
            content.append("\n".join([f"- {result.name}" for result in lock_success]))

        # Add any lock fail names and reason to the summary message
        lock_fail = [result for result in results if not result.success]
        if lock_fail:
            content.append("### Fail")
            content.append(
                "\n".join(
                    [f"- {result.name} - *`{result.msg}`*" for result in lock_fail]
                )
            )

        # Send queue lock summary message
        return await interaction.followup.send("\n".join(content), ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock an existing queue")
    async def _unlock_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None

        # Check if any queues are unlockable
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)
        is_admin = await self.bot.settings_manager.is_admin(
            interaction.guild_id,
            interaction.user.id,
        )
        unlockable_queues = [
            name
            for name, entry in queues.items()
            if entry.locked
            and not entry.in_progress
            and (interaction.user.id == entry.owner_id or is_admin)
        ]
        if not unlockable_queues:
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_NO_UNLOCKABLE, **ephemeral()
            )

        # Send queue unlock modal
        queue_unlock_modal = QueueUnlockModal(self.bot, sorted(unlockable_queues))
        await interaction.response.send_modal(queue_unlock_modal)

        # Wait until interaction has finished
        await queue_unlock_modal.wait()

        # If an invalid response was received, do not proceed
        if not queue_unlock_modal.is_valid:
            return

        # Attempt to lock all selected queues
        results: list[QueueOperationResult] = []

        for name in queue_unlock_modal.selected_queue_names:
            msg = None
            try:
                await self.bot.queue_manager.set_queue_lock_state(
                    interaction.guild_id,
                    interaction.user.id,
                    name,
                    False,
                    admin=is_admin,
                )
            except QueueDoesNotExist:
                msg = Canned.ERR_QUEUE_NO_EXISTS
            except QueueLockStateError:
                msg = Canned.ERR_QUEUE_LOCKSTATE_U
            except QueueProgressStateError:
                msg = Canned.ERR_QUEUE_PROGSTATE
            except Exception as e:  # noqa: BLE001
                msg = f"An error has occurred: {e}"
            finally:
                results.append(
                    QueueOperationResult.parse(
                        {
                            "name": titlecase(name),
                            "success": msg is None,
                            "msg": msg,
                        }
                    )
                )

        # Craft lock summary message
        content = [
            "## Queue Unlock Summary",
            "*The following is a message detailing all queue unlock attempts "
            + "based on the queues you selected*",
        ]

        # Add any unlock success names to the summary message
        unlock_success = [result for result in results if result.success]
        if unlock_success:
            content.append("### Success")
            content.append("\n".join([f"- {result.name}" for result in unlock_success]))

        # Add any unlock fail names and reason to the summary message
        unlock_fail = [result for result in results if not result.success]
        if unlock_fail:
            content.append("### Fail")
            content.append(
                "\n".join(
                    [f"- {result.name} - *`{result.msg}`*" for result in unlock_fail]
                )
            )

        # Send queue unlock summary message
        return await interaction.followup.send("\n".join(content), ephemeral=True)

    @app_commands.command(
        name="notify", description="Set queue notifications for queues you own"
    )
    async def _notify_queue(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None

        # Check for owned queues
        owned_queues = await self.bot.queue_manager.get_queues_owned_by(
            interaction.guild_id, interaction.user.id
        )
        if not owned_queues:
            return await interaction.response.send_message(
                Canned.ERR_QUEUE_OWNERSHIP, **ephemeral()
            )

        # Send queue notify modal
        queue_notify_modal = QueueNotifyModal(self.bot, owned_queues)
        await interaction.response.send_modal(queue_notify_modal)

        # Wait until interaction has finished
        await queue_notify_modal.wait()

        # If an invalid response was received, do not proceed
        if not queue_notify_modal.is_valid:
            return

        # If no changes were made, confirm and exit
        if not queue_notify_modal.diff:
            return await interaction.followup.send(
                "## No Changes Made\nThere have been no modifications made to "
                + "the notification statuses for your queues.",
            )

        # Set notify for the queues according to user specification
        notify_to_text = lambda n: "ON" if n else "OFF"
        changes: list[str] = []
        for name, notify_value in queue_notify_modal.diff:
            await self.bot.queue_manager.set_notify_state(
                interaction.guild_id, name, notify_value
            )
            changes.append(
                f"- **`{name}`** (`{notify_to_text(not notify_value)}` → `{notify_to_text(notify_value)}`)"
            )

        # Send confirmation message
        await interaction.followup.send(
            "\n".join(
                [
                    "## Queue Notification Status Changes",
                    "The following changes have been made:",
                    *changes,
                ]
            ),
            ephemeral=True,
        )

    @app_commands.command(name="list", description="List all queues with filters")
    @app_commands.rename(queue_type="type")
    @app_commands.describe(
        member="Filter only queues this member is a part of",
        queue_type="Filter only queues of this type",
    )
    async def _list_queue(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
        queue_type: QueueType | None = None,
    ):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None

        msg = None
        _ephemeral = True
        try:
            # Obtain list of criteria submitted
            criteria = []
            if member:
                criteria.append(f"Member {member.mention}")
            if queue_type:
                criteria.append(f"Type {queue_type}")

            # Filter results by submitted criteria and convert to list
            all_filtered_queues: dict[
                str, QueueEntry
            ] = await self.bot.queue_manager.list_queues(
                interaction.guild_id,
                member=member,
                queue_type=queue_type,
            )
            results: list[tuple[str, QueueEntry]] = [
                (name, entry) for name, entry in all_filtered_queues.items()
            ]

            # Initialise QueueListView
            qlview = QueueListView(
                source_interaction=interaction,
                data=results,
                criteria=criteria,
            )
            qlview.init_components()

            # Send message containing interactive QueueListView
            await interaction.response.send_message(
                view=qlview,
                allowed_mentions=discord.AllowedMentions.none(),
                ephemeral=_ephemeral,
            )
        except NoListResults:
            msg = Canned.ERR_QUEUE_NO_LIST_RESULTS
        except Exception as e:  # noqa: BLE001
            msg = f"An error has occurred: {e}"
            self.bot.logger.error(
                f"An exception occurred when trying to list queue: {e}"
            )
            traceback.print_exception(type(e), e, e.__traceback__)
            _ephemeral = False
        finally:
            if msg:
                await interaction.response.send_message(msg, ephemeral=_ephemeral)


async def setup(bot):
    await bot.add_cog(QueueCog(bot))
