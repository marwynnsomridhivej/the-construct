import traceback
from typing import Coroutine, Dict, List

import discord
from discord.ext import commands

from canned import Canned
from event import *
from exceptions import *
from queuemanager import ALL_R6_QUEUE_TYPES, QueueType


class MonitoringCog(commands.Cog):
    def __init__(self, bot):
        from bot import Bot
        self.bot: Bot = bot

    async def cog_load(self):
        _handlers: Dict[Coroutine, Event] = {
            # Custom Events
            self.queue_match_cleanup: Event.MATCH_FINALISED,
            self.delete_vcs: Event.MATCH_FINALISED,
            self.delete_dms: Event.MATCH_FINALISED,
            self.explicit_delete_dms: Event.PREMATCH_DM_DELETE,
            self.increment_match_count: Event.MATCH_FINALISED,
            self.thread_cleanup: Event.THREAD_CLEANUP,
            self.reset_move_back: Event.RESET_BUTTON_PRESSED,
            self.vc_delete_reset_cancel: Event.CANCEL_BUTTON_PRESSED,

            # DPY Events
            self._on_raw_member_remove: "raw_member_remove",
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[MonitoringCog] Successfully loaded")

    # =============================================
    # ================CUSTOM EVENTS================
    # =============================================

    async def _move_everyone_to_lobby_vc(self, temp_vc_id: int, lobby_vc_id: int, reason: Reason) -> None:
        temp_vc = self.bot.get_channel(temp_vc_id)
        lobby_vc = self.bot.get_channel(lobby_vc_id)

        if temp_vc is None or lobby_vc is None:
            return

        for member in temp_vc.members:
            await member.move_to(lobby_vc, reason=reason)

    async def _delete_dms(self, guild_id: int, players: List[int]) -> None:
        for player in players:
            try:
                message_id = await self.bot.dm_manager.delete(
                    guild_id, player)
                dm_channel = await self.bot.get_user(player).create_dm()
                await dm_channel.get_partial_message(message_id).delete()
                self.bot.logger.info(
                    f"Deleted message ID {message_id} for user {player}")
            except KeyError:
                self.bot.logger.info(
                    f"Message does not exist for guild_id {guild_id} user_id {player}")
            except discord.NotFound:
                self.bot.logger.info(
                    f"Message ID {message_id} for user {player} was already deleted")
            except discord.HTTPException as e:
                self.bot.logger.error(
                    f"HTTPException when trying to delete message ID {message_id} for user {player}: {e}")
            except Exception as e:
                self.bot.logger.error(
                    "An exception occurred when trying to delete " +
                    f"message ID {message_id} for user {player}: {e}"
                )
                traceback.print_exception(type(e), e, e.__traceback__)

    async def delete_vcs(self, payload: MatchFinalisedPayload) -> None:
        # Don't do anything if it is a 1v1, since no separate VCs were created
        if payload.queue_type == QueueType.R6_1V1:
            return

        for team in payload.teams:
            try:
                await self._move_everyone_to_lobby_vc(
                    team.voice_channel_id,
                    payload.lobby_vc_id,
                    Reason.MATCH_FINALISED_LOBBY_MOVE
                )
            except discord.HTTPException:
                pass

            # After moving everyone, THEN delete the VC
            await self.bot.get_channel(team.voice_channel_id).delete(reason=Reason.MATCH_FINALISED_DEL_TEMP)

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

    async def delete_dms(self, payload: MatchFinalisedPayload) -> None:
        for team in payload.teams:
            await self._delete_dms(payload.guild_id, team.players)

    async def explicit_delete_dms(self, payload: DMDeletePayload) -> None:
        await self._delete_dms(payload.guild_id, payload.players)

    async def increment_match_count(self, payload: MatchFinalisedPayload) -> None:
        await self.bot.stats_manager.increment_season_match_count(payload.guild_id, queue_type=payload.queue_type)

    async def thread_cleanup(self, payload: PrematchPayload) -> None:
        thread_channel: discord.Thread = self.bot.get_channel(
            payload.text_channel_id)
        if not isinstance(thread_channel, discord.Thread):
            self.bot.logger.error(
                f"Could not find thread channel with ID {payload.text_channel_id}")

        await thread_channel.edit(
            archived=True,
            locked=True,
            reason=Canned.R6DRAFT_THREAD_CLEANUP,
        )

    async def reset_move_back(self, payload: VCResetPayload) -> None:
        for team in payload.teams:
            await self._move_everyone_to_lobby_vc(
                team.voice_channel_id,
                payload.lobby_vc_id,
                Reason.VIEW_RESET_STATE,
            )

    async def vc_delete_reset_cancel(self, payload: VCResetPayload) -> None:
        for team in payload.teams:
            await self._move_everyone_to_lobby_vc(
                team.voice_channel_id,
                payload.lobby_vc_id,
                Reason.VIEW_RESET_STATE,
            )

            team_voice_channel = self.bot.get_channel(team.voice_channel_id)
            if team_voice_channel is None:
                continue
            await team_voice_channel.delete(reason=Reason.VC_DECONSTRUCT)

    # =============================================
    # =================DPY EVENTS==================
    # =============================================

    async def _on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        was_banned = False
        try:
            was_banned = isinstance(await guild.fetch_ban(payload.user), discord.BanEntry)
        except Exception:
            pass

        # Leave all queues the user is in, so long as it is not currently in progress (in an active match)
        try:
            queues = await self.bot.queue_manager.list_queues(payload.guild_id, member=payload.user)
            for name in queues.keys():
                try:
                    await self.bot.queue_manager.leave_user_from_queue(payload.guild_id, payload.user.id, name, force=True)
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
                        user_id=payload.user.id
                    )
            except ValueError:
                pass
            except PlayerDoesNotExist:
                pass


async def setup(bot):
    await bot.add_cog(MonitoringCog(bot))
