from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from canned import Canned
from event import (
    DMDeletePayload,
    Event,
    MatchFinalisedPayload,
    MatchPayload,
    Reason,
    VCResetPayload,
)
from exceptions import (
    NoListResults,
    NotInQueue,
    PlayerDoesNotExist,
    QueueDoesNotExist,
    QueueIsLocked,
    QueueProgressStateError,
)
from queuemanager import ALL_R6_QUEUE_TYPES, QueueType
from util import EventHandlerType

if TYPE_CHECKING:
    from bot import Bot


class MonitoringCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot
        self.r6view_to_watch: dict[int, MatchPayload] = {}

    async def cog_load(self):
        _handlers: dict[EventHandlerType, str] = {
            # Custom Events
            self.register_r6view_to_watch: Event.REGISTER_MATCH_WATCH,
            self.unregister_r6view_to_watch: Event.UNREGISTER_MATCH_WATCH,
            self.queue_match_cleanup: Event.MATCH_FINALISED,
            self.delete_vcs: Event.MATCH_FINALISED,
            self.delete_dms_after_match: Event.MATCH_FINALISED,
            self.explicit_delete_dms: Event.PREMATCH_DM_DELETE,
            self.increment_match_count: Event.MATCH_FINALISED,
            self.thread_cleanup: Event.THREAD_CLEANUP,
            self.reset_move_back: Event.RESET_BUTTON_PRESSED,
            self.vc_delete_reset_cancel: Event.CANCEL_BUTTON_PRESSED,
            # DPY Events
            self._on_raw_member_remove: "raw_member_remove",
            self._on_raw_message_delete: "raw_message_delete",
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[MonitoringCog] Successfully loaded")

    # ==============================================
    # ===============HELPER FUNCTIONS===============
    # ==============================================

    async def _move_everyone_to_lobby_vc(
        self, temp_vc_id: int, lobby_vc_id: int, reason: Reason
    ) -> None:
        """Helper function that moves every connected voice client
        from the temporary voice channel to the lobby voice channel.

        Args:
            temp_vc_id (int): The ID of the temporary voice channel.
            lobby_vc_id (int): The ID of the lobby voice channel.
            reason (Reason): Reason that will show up in audit logs
                for the move event.
        """
        temp_vc = self.bot.get_channel(temp_vc_id)
        lobby_vc = self.bot.get_channel(lobby_vc_id)

        if not (
            isinstance(temp_vc, discord.VoiceChannel)
            and isinstance(lobby_vc, discord.VoiceChannel)
        ):
            return

        for member in temp_vc.members:
            try:
                await member.move_to(lobby_vc, reason=reason)
            except discord.HTTPException:
                self.bot.logger.error(
                    f"Could not move member {member.display_name} ({member.id}) to lobby voice channel {lobby_vc_id}"
                )

    async def _delete_dms(self, guild_id: int, players: list[int]) -> None:
        """Delete stored prematch DMs for players when a match concludes.

        Args:
            guild_id (int): The ID of the guild the match took place in.
            players (list[int]): A list of player IDs that participated
                in the match and were sent a prematch DM when the match
                was started
        """
        for player in players:
            message_id = None
            try:
                message_id = await self.bot.dm_manager.delete(guild_id, player)
                user = self.bot.get_user(player)
                if user is None:
                    continue
                dm_channel = await user.create_dm()
                await dm_channel.get_partial_message(message_id).delete()
                self.bot.logger.info(
                    f"Deleted message ID {message_id} for user {player}"
                )
            except KeyError:
                self.bot.logger.info(
                    f"Message does not exist for guild_id {guild_id} user_id {player}"
                )
            except discord.NotFound:
                self.bot.logger.info(
                    f"Message ID {message_id} for user {player} was already deleted"
                )
            except discord.HTTPException as e:
                self.bot.logger.error(
                    f"HTTPException when trying to delete message ID {message_id} for user {player}: {e}"
                )
            except Exception as e:
                self.bot.logger.error(
                    "An exception occurred when trying to delete "
                    + f"message ID {message_id} for user {player}: {e}"
                )
                traceback.print_exception(type(e), e, e.__traceback__)

    # =============================================
    # ================CUSTOM EVENTS================
    # =============================================

    async def register_r6view_to_watch(self, payload: MatchPayload) -> None:
        """Add the message ID of a match panel to be checked for upon
        receiving a on_raw_message_delete event. This allows for detection
        and restoration of prematurely deleted match panels.

        Args:
            payload (MatchPayload): The MatchPayload instance.
        """
        self.r6view_to_watch[payload.r6view_message_id] = payload

    async def unregister_r6view_to_watch(self, message_id: int) -> None:
        """Remove the message ID of a match panel from the watchlist.
        This allows its permanent deletion without restoration.

        Args:
            message_id (int): The ID of the message containing the
                match panel.
        """
        if message_id in self.r6view_to_watch.keys():
            del self.r6view_to_watch[message_id]

    async def delete_vcs(self, payload: MatchFinalisedPayload) -> None:
        """Delete team voice channels upon match completion.

        Args:
            payload (MatchFinalisedPayload): The MatchFinalisedPayload
                generated upon match completion.
        """
        # Don't do anything if it is a 1v1, since no separate VCs were created
        if payload.queue_type == QueueType.R6_1V1:
            return

        for team in payload.teams:
            # Ensure team voice channel ID is set
            team_vc_id = team.voice_channel_id
            if team_vc_id is None:
                continue

            try:
                await self._move_everyone_to_lobby_vc(
                    team_vc_id,
                    payload.lobby_vc_id,
                    Reason.MATCH_FINALISED_LOBBY_MOVE,
                )
            except discord.HTTPException:
                self.bot.logger.error(
                    f"Unable to move voice clients from voice channel ID {team_vc_id} to {payload.lobby_vc_id}"
                )

            # After moving everyone, THEN delete the VC
            team_vc = self.bot.get_channel(team_vc_id)
            if not isinstance(team_vc, discord.VoiceChannel):
                continue

            try:
                await team_vc.delete(reason=Reason.MATCH_FINALISED_DEL_TEMP)
            except discord.HTTPException:
                self.bot.logger.error(
                    f"Unable to delete the voice channel with ID: {team_vc_id}"
                )

    async def queue_match_cleanup(self, payload: MatchFinalisedPayload) -> None:
        """Delete a queue entry from the database upon match completion.

        Args:
            payload (MatchFinalisedPayload): The MatchFinalisedPayload
                generated upon match completion.
        """
        await self.bot.queue_manager.delete_queue(
            payload.guild_id,
            payload.name,
            payload.owner_id,
        )
        await self.bot.match_manager.delete_match(
            payload.guild_id,
            payload.name,
        )
        del self.r6view_to_watch[payload.r6view_message_id]

    async def delete_dms_after_match(self, payload: MatchFinalisedPayload) -> None:
        """Delete prematch DMs sent to all players participating in the
        match upon match completion.

        Args:
            payload (MatchFinalisedPayload): The MatchFinalisedPayload
                generated upon match completion.
        """
        for team in payload.teams:
            await self._delete_dms(payload.guild_id, team.players)

    async def explicit_delete_dms(self, payload: DMDeletePayload) -> None:
        """Delete prematch DMs sent to all players participating in the
        match upon match cancellation.

        Args:
            payload (DMDeletePayload): The DMDeletePayload generated
                upon match cancellation.
        """
        await self._delete_dms(payload.guild_id, payload.players)

    async def increment_match_count(self, payload: MatchFinalisedPayload) -> None:
        """Increment the match count in the current active season upon
        match completion.

        Args:
            payload (MatchFinalisedPayload): The MatchFinalisedPayload
                generated upon match completion.
        """
        await self.bot.stats_manager.increment_season_match_count(
            payload.guild_id, queue_type=payload.queue_type
        )

    async def thread_cleanup(self, payload: MatchPayload) -> None:
        """Close and lock the thread containing the match panel upon
        match completion or cancellation.

        Args:
            payload (MatchPayload): The MatchPayload generated upon
                prematch setup completion.
        """
        thread_channel = self.bot.get_channel(payload.text_channel_id)
        if not isinstance(thread_channel, discord.Thread):
            return self.bot.logger.error(
                f"Could not find thread channel with ID {payload.text_channel_id}"
            )

        try:
            await thread_channel.edit(
                archived=True,
                locked=True,
                reason=Canned.R6DRAFT_THREAD_CLEANUP,
            )
        except discord.HTTPException:
            self.bot.logger.error(
                f"Unable to lock and archive the thread channel with ID {payload.text_channel_id}"
            )

    async def reset_move_back(self, payload: VCResetPayload) -> None:
        """Move all players back to the lobby voice channel.

        Args:
            payload (VCResetPayload): The VCResetPayload generated
                (can occur in multiple instances)
        """
        for team in payload.teams:
            if team.voice_channel_id is None:
                continue

            await self._move_everyone_to_lobby_vc(
                team.voice_channel_id,
                payload.lobby_vc_id,
                Reason.VIEW_RESET_STATE,
            )

    async def vc_delete_reset_cancel(self, payload: VCResetPayload) -> None:
        """Delete team specific voice channels upon resetting the match
        panel or match cancellation.

        Args:
            payload (VCResetPayload): The VCResetPayload generated upon
            resetting the match panel or match cancellation.
        """
        for team in payload.teams:
            # Ensure team voice channel ID is set
            team_vc_id = team.voice_channel_id
            if team_vc_id is None:
                continue

            await self._move_everyone_to_lobby_vc(
                team_vc_id,
                payload.lobby_vc_id,
                Reason.VIEW_RESET_STATE,
            )

            team_vc = self.bot.get_channel(team_vc_id)
            if not isinstance(team_vc, discord.VoiceChannel):
                continue

            try:
                await team_vc.delete(reason=Reason.VC_DECONSTRUCT)
            except discord.HTTPException:
                self.bot.logger.error(
                    f"Unable to delete the team voice channel with ID: {team.voice_channel_id}"
                )

    # =============================================
    # =================DPY EVENTS==================
    # =============================================

    async def _on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        """Handle players leaving the server. If they left due to a ban,
        their stats for the current active season are completely deleted.

        Args:
            payload (discord.RawMemberRemoveEvent): The payload
                dispatched when a user leaves a server.
        """
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        was_banned = False
        try:
            was_banned = isinstance(
                await guild.fetch_ban(payload.user), discord.BanEntry
            )
        except Exception:
            pass

        # Leave all queues the user is in, so long as it is not currently in progress (in an active match)
        try:
            queues = await self.bot.queue_manager.list_queues(
                payload.guild_id,
                member=payload.user,
            )
            for name in queues.keys():
                try:
                    await self.bot.queue_manager.leave_user_from_queue(
                        payload.guild_id, payload.user.id, name, force=True
                    )
                except QueueDoesNotExist:
                    pass
                except QueueProgressStateError:
                    pass
                except QueueIsLocked:
                    pass
                except NotInQueue:
                    pass
        except NoListResults:
            pass

        # If the user was banned, delete their stat entry for the current season (if it exists)
        if was_banned:
            try:
                await self.bot.stats_manager.ensure_season(guild_id=payload.guild_id)
                for queue_type in ALL_R6_QUEUE_TYPES:
                    await self.bot.stats_manager.delete_player(
                        guild_id=payload.guild_id,
                        queue_type=queue_type,
                        user_id=payload.user.id,
                    )
            except ValueError:
                pass
            except PlayerDoesNotExist:
                pass

    async def _on_raw_message_delete(
        self, event_payload: discord.RawMessageDeleteEvent
    ) -> None:
        """Check for premature deletions of any active match panel
        and restore it if necessary.

        Args:
            event_payload (discord.RawMessageDeleteEvent): The payload
                dispatched when a message is deleted.
        """
        # If the message ID isn't one that was watched, disregard
        if event_payload.message_id not in self.r6view_to_watch.keys():
            return

        # Try to get the channel the message was deleted in (should be thread)
        channel = self.bot.get_channel(event_payload.channel_id)

        # Skip if channel could not be found for any reason
        if not isinstance(channel, discord.Thread):
            return

        # Acquire the associated data payload
        data_payload = self.r6view_to_watch[event_payload.message_id]

        # Try to resend the R6View its state up until the message deletion
        try:
            message = await channel.send(view=data_payload.r6view)
        except discord.HTTPException:
            # If for any reason the message cannot be sent cancel the match
            await self.bot.match_manager.delete_match(
                data_payload.guild_id,
                data_payload.match_name,
            )

            # Then set the progress and lock states back to False
            await self.bot.queue_manager.set_progress_state(
                data_payload.guild_id,
                data_payload.match_name,
                False,
            )
            await self.bot.queue_manager.set_queue_lock_state(
                data_payload.guild_id,
                0,
                data_payload.match_name,
                False,
                admin=True,
            )

            # Set match canceled in R6View to True and stop responding to interactions
            data_payload.r6view.match_canceled = True
            data_payload.r6view.stop()

            # Teardown any created voice channels
            if data_payload.match_entry is not None:
                self.bot.dispatch(
                    Event.CANCEL_BUTTON_PRESSED,
                    VCResetPayload.create(
                        data_payload.guild_id,
                        data_payload.match_entry.voice_channel_id,
                        data_payload.r6view.teams,
                        data_payload.r6view.match.type,
                    ),
                )

            # Clean up the thread
            self.bot.dispatch(Event.THREAD_CLEANUP, data_payload)
        else:
            # If message sending was successful, watch it
            data_payload.set_r6view_message_id(message.id)
            self.bot.dispatch(Event.REGISTER_MATCH_WATCH, data_payload)
        finally:
            # Unregister the old reference
            self.bot.dispatch(Event.UNREGISTER_MATCH_WATCH, event_payload.message_id)


async def setup(bot):
    await bot.add_cog(MonitoringCog(bot))
