from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from canned import Canned
from event import Event, QueueFilledPayload
from exceptions import (
    AlreadyInQueue,
    NoListResults,
    NotInQueue,
    NotQueueOwner,
    QueueAlreadyExists,
    QueueDoesNotExist,
    QueueIsFull,
    QueueIsLocked,
    QueueLimitReached,
    QueueLockStateError,
    QueueProgressStateError,
)
from queuemanager import QueueEntry, QueueType
from ui import QueueFilledDMView, QueueListView
from util import EventHandlerType

if TYPE_CHECKING:
    from bot import Bot


@app_commands.guild_only()
class QueueCog(commands.GroupCog, name="queue"):
    def __init__(self, bot):
        self.bot: Bot = bot

    async def cog_load(self):
        _handlers: dict[EventHandlerType, Event] = {
            self._notify_queue_owner_full: Event.QUEUE_FILLED,
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[QueueCog] Successfully loaded")

    async def _notify_queue_owner_full(self, payload: QueueFilledPayload) -> None:
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
    @app_commands.rename(queue_type="type")
    @app_commands.describe(
        queue_type="The ruleset used for this queue",
        name="The name given to this queue instance",
    )
    async def _create_queue(
        self, interaction: discord.Interaction, queue_type: QueueType, name: str
    ):
        msg = None
        ephemeral = True
        try:
            await self.bot.queue_manager.create_queue(
                guild_id=interaction.guild_id,  # type: ignore
                owner_id=interaction.user.id,
                name=name,
                queue_type=queue_type,
            )
            msg = f'The queue "{name}" has been created for {queue_type}'
            ephemeral = False
        except QueueLimitReached:
            msg = Canned.ERR_QUEUE_LIMIT
        except QueueAlreadyExists:
            msg = Canned.ERR_QUEUE_EXISTS
        except ValueError:
            msg = Canned.ERR_QUEUE_NAME_LEN
        except Exception as e:
            msg = f"An error has occurred: {e}"
            ephemeral = False
        finally:
            if msg:
                await interaction.response.send_message(msg, ephemeral=ephemeral)

    @app_commands.command(name="delete", description="Delete a queue you created")
    @app_commands.describe(name="The name of the queue you are trying to delete")
    async def _delete_queue(self, interaction: discord.Interaction, name: str):
        msg = None
        ephemeral = True
        try:
            await self.bot.queue_manager.delete_queue(
                interaction.guild_id,  # type: ignore
                name,
                interaction.user.id,
            )
            msg = f'Successfully deleted the queue "{name}"'
            ephemeral = False
        except QueueDoesNotExist:
            msg = Canned.ERR_QUEUE_NO_EXISTS
        except NotQueueOwner:
            msg = Canned.ERR_QUEUE_OWNER
        except Exception as e:
            msg = f"An error has occurred: {e}"
            ephemeral = False
        finally:
            if msg:
                await interaction.response.send_message(msg, ephemeral=ephemeral)

    @_delete_queue.autocomplete("name")
    async def _delete_queue_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)  # type: ignore
        owned_queues = [
            name
            for name, entry in queues.items()
            if entry.owner_id == interaction.user.id
        ]
        return self.get_sorted_choices(owned_queues, current)

    @app_commands.command(name="join", description="Join an existing queue")
    @app_commands.describe(name="The name of the queue you are trying to join")
    async def _join_queue(self, interaction: discord.Interaction, name: str):
        msg = None
        ephemeral = True
        try:
            q = await self.bot.queue_manager.join_user_to_queue(
                interaction.guild_id,  # type: ignore
                interaction.user.id,
                name,
            )
            msg = f'You successfully joined the queue "{name}"'
        except QueueDoesNotExist:
            msg = Canned.ERR_QUEUE_NO_EXISTS
        except AlreadyInQueue:
            msg = Canned.ERR_QUEUE_ALREADY_IN
        except QueueIsFull:
            msg = Canned.ERR_QUEUE_FULL
        except QueueIsLocked:
            msg = Canned.ERR_QUEUE_LOCKED_JOIN
        except Exception as e:
            msg = f"An error has occurred: {e}"
            ephemeral = False
        else:
            if q.full:
                # Notify the queue owner that their queue has been filled
                self.bot.dispatch(
                    Event.QUEUE_FILLED,
                    QueueFilledPayload(
                        {
                            "guild_id": interaction.guild_id,
                            "name": name,
                            "entry": q,
                        }
                    ),
                )
        finally:
            if msg:
                await interaction.response.send_message(msg, ephemeral=ephemeral)

    @_join_queue.autocomplete("name")
    async def _join_queue_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)  # type: ignore
        joinable_queues = [
            name
            for name, entry in queues.items()
            if len(entry.players) < entry.max_players
            and interaction.user.id not in entry.players
        ]
        return self.get_sorted_choices(joinable_queues, current)

    @app_commands.command(name="leave", description="Leave an existing queue")
    @app_commands.describe(name="The name of the queue you are trying to leave")
    async def _leave_queue(self, interaction: discord.Interaction, name: str):
        msg = None
        ephemeral = True
        try:
            await self.bot.queue_manager.leave_user_from_queue(
                interaction.guild_id,  # type: ignore
                interaction.user.id,
                name,
            )
            msg = f'You successfully left the queue "{name}"'
        except QueueDoesNotExist:
            msg = Canned.ERR_QUEUE_NO_EXISTS
        except NotInQueue:
            msg = Canned.ERR_QUEUE_NOT_IN
        except QueueIsLocked:
            msg = Canned.ERR_QUEUE_LOCKED_LEAVE
        except Exception as e:
            msg = f"An error has occurred: {e}"
            ephemeral = False
        finally:
            if msg:
                await interaction.response.send_message(msg, ephemeral=ephemeral)

    @_leave_queue.autocomplete("name")
    async def _leave_queue_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)  # type: ignore
        leaveable_queues = [
            name
            for name, entry in queues.items()
            if interaction.user.id in entry.players
        ]
        return self.get_sorted_choices(leaveable_queues, current)

    @app_commands.command(name="lock", description="Lock an existing queue")
    @app_commands.describe(name="The name of the queue you are trying to lock")
    async def _lock_queue(self, interaction: discord.Interaction, name: str):
        msg = None
        ephemeral = True
        try:
            await self.bot.queue_manager.set_queue_lock_state(
                interaction.guild_id,  # type: ignore
                interaction.user.id,
                name,
                True,
            )
            msg = f'Queue "{name}" has been locked'
            ephemeral = False
        except QueueDoesNotExist:
            msg = Canned.ERR_QUEUE_NO_EXISTS
        except QueueLockStateError:
            msg = Canned.ERR_QUEUE_LOCKSTATE_L
        except NotQueueOwner:
            msg = Canned.ERR_QUEUE_OWNER
        except QueueProgressStateError:
            msg = Canned.ERR_QUEUE_PROGSTATE
        except Exception as e:
            msg = f"An error has occurred: {e}"
            ephemeral = False
        finally:
            if msg:
                await interaction.response.send_message(msg, ephemeral=ephemeral)

    @_lock_queue.autocomplete("name")
    async def _lock_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)  # type: ignore
        lockable_queues = [
            name
            for name, entry in queues.items()
            if not entry.locked and interaction.user.id == entry.owner_id
        ]
        return self.get_sorted_choices(lockable_queues, current)

    @app_commands.command(name="unlock", description="Unlock an existing queue")
    @app_commands.describe(name="The name of the queue you are trying to unlock")
    async def _unlock_queue(self, interaction: discord.Interaction, name: str):
        msg = None
        ephemeral = True
        try:
            await self.bot.queue_manager.set_queue_lock_state(
                interaction.guild_id,  # type: ignore
                interaction.user.id,
                name,
                False,
            )
            msg = f'Queue "{name}" has been unlocked'
            ephemeral = False
        except QueueDoesNotExist:
            msg = Canned.ERR_QUEUE_NO_EXISTS
        except QueueLockStateError:
            msg = Canned.ERR_QUEUE_LOCKSTATE_U
        except NotQueueOwner:
            msg = Canned.ERR_QUEUE_OWNER
        except QueueProgressStateError:
            msg = Canned.ERR_QUEUE_PROGSTATE
        except Exception as e:
            msg = f"An error has occurred: {e}"
            ephemeral = False
        finally:
            if msg:
                await interaction.response.send_message(msg, ephemeral=ephemeral)

    @_unlock_queue.autocomplete("name")
    async def _unlock_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        queues = await self.bot.queue_manager.get_all_queues(interaction.guild_id)  # type: ignore
        unlockable_queues = [
            name
            for name, entry in queues.items()
            if entry.locked and interaction.user.id == entry.owner_id
        ]
        return self.get_sorted_choices(unlockable_queues, current)

    @app_commands.command(name="list", description="List all queues with filters")
    @app_commands.rename(queue_type="type")
    @app_commands.describe(
        member="Filter only queues this member is a part of",
        queue_type="Filter only queues of this type",
    )
    async def _list_queue(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
        queue_type: Optional[QueueType] = None,
    ):
        msg = None
        ephemeral = True
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
                interaction.guild_id,  # type: ignore
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
                ephemeral=ephemeral,
            )
        except NoListResults:
            msg = Canned.ERR_QUEUE_NO_LIST_RESULTS
        except Exception as e:
            msg = f"An error has occurred: {e}"
            self.bot.logger.error(
                f"An exception occurred when trying to list queue: {e}"
            )
            traceback.print_exception(type(e), e, e.__traceback__)
            ephemeral = False
        finally:
            if msg:
                await interaction.response.send_message(msg, ephemeral=ephemeral)

    @staticmethod
    def get_sorted_choices(
        entries: list[str], current: str
    ) -> list[app_commands.Choice[str]]:
        choices = [
            app_commands.Choice(name=choice, value=choice)
            for choice in entries
            if current.lower() in choice.lower()
        ]
        return sorted(choices, key=lambda x: x.name)


async def setup(bot):
    await bot.add_cog(QueueCog(bot))
