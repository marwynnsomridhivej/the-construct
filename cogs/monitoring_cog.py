from __future__ import annotations

import traceback
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, Dict, List, Union

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

if TYPE_CHECKING:
    from bot import Bot

    type Coro = Coroutine[Any, Any, None]
    type Handler = Union[
        Callable[[MatchPayload], Coro],
        Callable[[MatchFinalisedPayload], Coro],
        Callable[[DMDeletePayload], Coro],
        Callable[[VCResetPayload], Coro],
        Callable[[discord.RawMemberRemoveEvent], Coro],
        Callable[[discord.RawMessageDeleteEvent], Coro],
        Callable[[int], Coro],
    ]


class MonitoringCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot
        self.r6view_to_watch: Dict[int, MatchPayload] = {}

    async def cog_load(self):
        _handlers: Dict[Handler, str] = {
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

    async def _delete_dms(self, guild_id: int, players: List[int]) -> None:
        for player in players:
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
                    f"Message ID {message_id} for user {player} was already deleted"  # type: ignore
                )
            except discord.HTTPException as e:
                self.bot.logger.error(
                    f"HTTPException when trying to delete message ID {message_id} for user {player}: {e}"  # type: ignore
                )
            except Exception as e:
                self.bot.logger.error(
                    "An exception occurred when trying to delete "
                    + f"message ID {message_id} for user {player}: {e}"  # type: ignore
                )
                traceback.print_exception(type(e), e, e.__traceback__)

    # =============================================
    # ================CUSTOM EVENTS================
    # =============================================

    async def register_r6view_to_watch(self, payload: MatchPayload) -> None:
        # Add payload to match panels to watch so the bot can detect
        # prematurely deleted R6View panels
        self.r6view_to_watch[payload.r6view_message_id] = payload

    async def unregister_r6view_to_watch(self, message_id: int) -> None:
        # Remove the payload associated with the provided message_id if one exists
        if message_id in self.r6view_to_watch.keys():
            del self.r6view_to_watch[message_id]

    async def delete_vcs(self, payload: MatchFinalisedPayload) -> None:
        # Don't do anything if it is a 1v1, since no separate VCs were created
        if payload.queue_type == QueueType.R6_1V1:
            return

        for team in payload.teams:
            try:
                await self._move_everyone_to_lobby_vc(
                    team.voice_channel_id,  # type: ignore
                    payload.lobby_vc_id,
                    Reason.MATCH_FINALISED_LOBBY_MOVE,
                )
            except discord.HTTPException:
                self.bot.logger.error(
                    f"Unable to move voice clients from voice channel ID {team.voice_channel_id} to {payload.lobby_vc_id}"
                )

            # After moving everyone, THEN delete the VC
            try:
                await self.bot.get_channel(team.voice_channel_id).delete(  # type: ignore
                    reason=Reason.MATCH_FINALISED_DEL_TEMP
                )
            except discord.HTTPException:
                self.bot.logger.error(
                    f"Unable to delete the voice channel with ID: {team.voice_channel_id}"
                )

    async def queue_match_cleanup(self, payload: MatchFinalisedPayload) -> None:
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
        for team in payload.teams:
            await self._delete_dms(payload.guild_id, team.players)

    async def explicit_delete_dms(self, payload: DMDeletePayload) -> None:
        await self._delete_dms(payload.guild_id, payload.players)

    async def increment_match_count(self, payload: MatchFinalisedPayload) -> None:
        await self.bot.stats_manager.increment_season_match_count(
            payload.guild_id, queue_type=payload.queue_type
        )

    async def thread_cleanup(self, payload: MatchPayload) -> None:
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
        for team in payload.teams:
            await self._move_everyone_to_lobby_vc(
                team.voice_channel_id,  # type: ignore
                payload.lobby_vc_id,
                Reason.VIEW_RESET_STATE,
            )

    async def vc_delete_reset_cancel(self, payload: VCResetPayload) -> None:
        for team in payload.teams:
            await self._move_everyone_to_lobby_vc(
                team.voice_channel_id,  # type: ignore
                payload.lobby_vc_id,
                Reason.VIEW_RESET_STATE,
            )

            team_voice_channel = self.bot.get_channel(team.voice_channel_id)  # type: ignore
            if not isinstance(team_voice_channel, discord.VoiceChannel):
                continue

            try:
                await team_voice_channel.delete(reason=Reason.VC_DECONSTRUCT)
            except discord.HTTPException:
                self.bot.logger.error(
                    f"Unable to delete the team voice channel with ID: {team.voice_channel_id}"
                )

    # =============================================
    # =================DPY EVENTS==================
    # =============================================

    async def _on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
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
                member=payload.user,  # type: ignore
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
            self.bot.dispatch(
                Event.CANCEL_BUTTON_PRESSED,
                VCResetPayload.create(
                    data_payload.guild_id,
                    data_payload.match_entry.voice_channel_id,  # type: ignore
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
