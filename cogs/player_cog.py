from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from canned import Canned
from event import Event, PlayerStatsResetPayload
from queuemanager import QueueType
from ui import ConfirmationModal, PlayerStatsDeleteDMView, PlayerStatsResetDMView
from util import EventHandlerType, ephemeral

if TYPE_CHECKING:
    from bot import Bot


@app_commands.guild_only()
class PlayerCog(commands.GroupCog, name="player"):
    def __init__(self, bot):
        self.bot: Bot = bot

    async def cog_load(self):
        _handlers: dict[EventHandlerType, Event] = {
            self.send_player_stats_reset_dm: Event.PLAYER_STATS_RESET,
            self.send_player_stats_delete_dm: Event.PLAYER_STATS_DELETE,
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[PlayerCog] Successfully loaded")

    async def send_player_stats_reset_dm(
        self, payload: PlayerStatsResetPayload
    ) -> None:
        """Send a DM to the player that just had their stats reset.

        Args:
            payload (PlayerStatsResetPayload): The PlayerStatsResetPayload
                generated from the /player reset command.
        """
        user = self.bot.get_user(payload.user_id)
        guild = self.bot.get_guild(payload.guild_id)
        if user is None or guild is None:
            return self.bot.logger.info(
                f"Unable to send player stats RESET DM for user_id={payload.user_id}, guild_id={payload.guild_id}, queue_type={payload.queue_type}"
            )

        await user.send(
            view=PlayerStatsResetDMView(
                user=user, guild=guild, queue_type=payload.queue_type
            )
        )

    async def send_player_stats_delete_dm(
        self, payload: PlayerStatsResetPayload
    ) -> None:
        """Send a DM to the player that just had their stats deleted.

        Args:
            payload (PlayerStatsResetPayload): The PlayerStatsResetPayload
                generated from the /player delete command.
        """
        user = self.bot.get_user(payload.user_id)
        guild = self.bot.get_guild(payload.guild_id)
        if user is None or guild is None:
            return self.bot.logger.info(
                f"Unable to send player stats DELETE DM for user_id={payload.user_id}, guild_id={payload.guild_id}, queue_type={payload.queue_type}"
            )

        await user.send(
            view=PlayerStatsDeleteDMView(
                user=user, guild=guild, queue_type=payload.queue_type
            )
        )

    async def _perform_checks(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        queue_type: QueueType,
    ) -> bool:
        """Perform checks before allowing any player command to execute.

        Args:
            interaction (discord.Interaction): The interaction context.
            member (discord.Member): The member that is being checked.
            queue_type (QueueType): The queue type of the stats to check.

        Returns:
            bool: Whether or not the command can be executed.
        """
        # Typehint assert, we know this is true anyway
        assert (
            interaction.guild_id is not None
            and interaction.guild is not None
            and interaction.guild.owner_id is not None
        )

        # Must be server owner or bot administrator
        if not (
            interaction.user.id == interaction.guild.owner_id
            or await self.bot.settings_manager.is_admin(
                interaction.guild_id,
                interaction.user.id,
            )
        ):
            await interaction.response.send_message(Canned.ERR_PERMS, **ephemeral())
            return False

        # Ensure specified member is not a bot user
        if member.bot:
            await interaction.response.send_message(Canned.ERR_BOT_USER, **ephemeral())
            return False

        # Ensure there is an active season
        try:
            await self.bot.stats_manager.ensure_season(guild_id=interaction.guild_id)
        except ValueError:
            await interaction.response.send_message(
                Canned.ERR_SEASON_NO_EXISTS, **ephemeral()
            )
            return False

        # Ensure specified member has stats (is ranked)
        all_players = await self.bot.stats_manager.get_guild_players(
            interaction.guild_id, queue_type
        )
        if not any([player.id == member.id for player in all_players]):
            await interaction.response.send_message(
                Canned.ERR_STATS_PLAYER_NO_RANKED, **ephemeral()
            )
            return False

        # Everything passed
        return True

    @app_commands.command(
        name="reset",
        description="Reset the stats for a player for the current active season of the specified queue type",
    )
    @app_commands.describe(
        member="The member for which stats are to be reset",
        queue_type="The desired queue type",
    )
    @app_commands.rename(queue_type="type")
    async def _reset_command(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        queue_type: QueueType,
    ):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None

        # Must pass all checks before confirmation modal is sent
        if not await self._perform_checks(interaction, member, queue_type):
            return

        # Send custom confirmation modal and wait until interaction is completed
        confirmation_modal = ConfirmationModal(
            operation="Reset Player Stats",
            custom={
                "yes": f"I understand and wish to reset their {queue_type} stats",
            },
        )
        await interaction.response.send_modal(confirmation_modal)
        await confirmation_modal.wait()

        # Cancel if user canceled the modal or explicitly selected no
        if not confirmation_modal.proceed:
            return

        # Reset stats and send confirmation messages
        await self.bot.stats_manager.reset_player(
            guild_id=interaction.guild_id, queue_type=queue_type, user_id=member.id
        )
        await interaction.followup.send(
            f"Player {member.mention}'s stats have been successfully reset for {queue_type}",
            ephemeral=True,
        )
        self.bot.dispatch(
            Event.PLAYER_STATS_RESET,
            PlayerStatsResetPayload.create(
                user_id=member.id,
                guild_id=interaction.guild_id,
                queue_type=queue_type,
            ),
        )

    @app_commands.command(
        name="delete",
        description="Delete the stats for a player for the current active season of the specified queue type",
    )
    @app_commands.describe(
        member="The member for which stats are to be deleted",
        queue_type="The desired queue type",
    )
    @app_commands.rename(queue_type="type")
    async def _delete_command(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        queue_type: QueueType,
    ):
        # Typehint assert, we know this is true anyway
        assert interaction.guild_id is not None

        # Must pass all checks before confirmation modal is sent
        if not await self._perform_checks(interaction, member, queue_type):
            return

        # Send custom confirmation modal and wait until interaction is completed
        confirmation_modal = ConfirmationModal(
            operation="Delete Player Stats",
            custom={
                "yes": f"I understand and wish to delete their {queue_type} stats",
            },
        )
        await interaction.response.send_modal(confirmation_modal)
        await confirmation_modal.wait()

        # Cancel if user canceled the modal or explicitly selected no
        if not confirmation_modal.proceed:
            return

        # Delete stats and send confirmation messages
        await self.bot.stats_manager.delete_player(
            guild_id=interaction.guild_id, queue_type=queue_type, user_id=member.id
        )
        await interaction.followup.send(
            f"Player {member.mention}'s stats have been successfully deleted for {queue_type}",
            ephemeral=True,
        )
        self.bot.dispatch(
            Event.PLAYER_STATS_DELETE,
            PlayerStatsResetPayload.create(
                user_id=member.id,
                guild_id=interaction.guild_id,
                queue_type=queue_type,
            ),
        )


async def setup(bot):
    await bot.add_cog(PlayerCog(bot))
