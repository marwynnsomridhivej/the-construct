from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from canned import Canned
from event import Event, SeasonEndPayload
from queuemanager import ALL_R6_QUEUE_TYPES, QueueType
from ui import ConfirmationModal, SeasonEndDMView, SeasonsListView, SeasonStartModal
from util import EventHandlerType, ephemeral

if TYPE_CHECKING:
    from bot import Bot


@app_commands.guild_only()
class SeasonCog(commands.GroupCog, name="season"):
    def __init__(self, bot):
        self.bot: Bot = bot

    async def cog_load(self):
        _handlers: dict[EventHandlerType, Event] = {
            self._send_season_end_dms: Event.SEASON_STOP
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[SeasonCog] Successfully loaded")

    async def _ensure_perms(self, interaction: discord.Interaction) -> bool:
        # Typehint assert, we know this is true anyway
        assert (
            (guild_id := interaction.guild_id) is not None
            and interaction.guild is not None
            and (owner_id := interaction.guild.owner_id) is not None
        )

        # Make sure user is either the server owner or is a bot administrator
        return (
            owner_id == interaction.user.id
            or await self.bot.settings_manager.is_admin(
                guild_id,
                interaction.user.id,
            )
        )

    async def _send_season_end_dms(self, payload: SeasonEndPayload) -> None:
        users_data: dict[discord.User, dict[QueueType, dict]] = {}

        for queue_type, players in payload.ranked_players.items():
            for rank, player in players:
                user = self.bot.get_user(player.id)
                if user is None:
                    continue
                if users_data.get(user) is None:
                    users_data[user] = {}
                users_data[user][queue_type] = {
                    "rank": rank,
                    "player": player,
                }

        for user, data in users_data.items():
            # Ensure guild is not None
            guild = self.bot.get_guild(payload.guild_id)
            if guild is None:
                continue

            try:
                await user.send(
                    view=SeasonEndDMView(
                        guild=guild,
                        season=payload.season,
                        data=data,
                    )
                )
            except discord.HTTPException as e:
                self.bot.logger.error(
                    f"An error occurred when trying to send the season end DM: {e.text}"
                )

    @app_commands.command(name="start", description="Starts a new season")
    async def _start_season(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert (guild_id := interaction.guild_id) is not None

        if not await self._ensure_perms(interaction):
            return await interaction.response.send_message(
                Canned.ERR_PERMS, **ephemeral()
            )

        try:
            # Check if a season exists
            await self.bot.stats_manager.ensure_season(guild_id=guild_id)
        except ValueError:
            # Error means no season, which is what we want
            pass
        else:
            # If no errors, means season exists, so we send error message here
            return await interaction.response.send_message(
                Canned.ERR_SEASON_EXISTS, **ephemeral()
            )

        season_start_modal = SeasonStartModal(bot=self.bot)
        await interaction.response.send_modal(season_start_modal)
        await season_start_modal.wait()
        name = season_start_modal.name

        # Make sure the specified name is not a duplicate
        if any(
            [
                name == season.name
                for season in await self.bot.stats_manager.get_all_seasons(guild_id)
            ]
        ):
            return await interaction.followup.send(
                Canned.ERR_SEASON_DUPLICATE_NAME, ephemeral=True
            )

        # Start a season in the guild with the specified name
        await self.bot.stats_manager.start_season(
            guild_id=guild_id, name=season_start_modal.name
        )
        await interaction.followup.send(
            f'Season "{season_start_modal.name}" has been started', ephemeral=True
        )

    @app_commands.command(name="stop", description="Stops the current active season")
    async def _stop_season(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert (guild_id := interaction.guild_id) is not None

        if not await self._ensure_perms(interaction):
            return await interaction.response.send_message(
                Canned.ERR_PERMS, **ephemeral()
            )

        try:
            # Ensure a season exists (so we can stop it lol)
            await self.bot.stats_manager.ensure_season(guild_id=guild_id)
        except ValueError:
            # If no season, send error message
            return await interaction.response.send_message(
                Canned.ERR_SEASON_NO_EXISTS, **ephemeral()
            )

        season_end_modal = ConfirmationModal(
            operation="Stop Season",
            custom={
                "yes": "I understand and wish to stop the current season",
            },
        )
        await interaction.response.send_modal(season_end_modal)
        await season_end_modal.wait()

        # Don't proceed if they cancel
        if not season_end_modal.proceed:
            return

        # Don't proceed if there are active matches in the current season
        if await self.bot.match_manager.has_running_match(guild_id):
            return await interaction.followup.send(
                Canned.ERR_SEASON_MIP, ephemeral=True
            )

        # Get season object and ranked players before season stop
        season = await self.bot.stats_manager.get_season(guild_id=guild_id)
        ranked_players = {
            queue_type: await self.bot.stats_manager.get_season_rankings(
                guild_id=guild_id, queue_type=queue_type
            )
            for queue_type in ALL_R6_QUEUE_TYPES
        }

        # Proceed to stop season
        await self.bot.stats_manager.stop_season(guild_id=guild_id)
        await interaction.followup.send(Canned.SEASON_STOP, ephemeral=True)
        await interaction.followup.send(Canned.SEASON_STOP_DM_CONF, ephemeral=True)

        # Dispatch season end event if there were active players in the season
        if any(
            [
                season.get_data_by_queue_type(queue_type).player_count > 0
                for queue_type in ALL_R6_QUEUE_TYPES
            ]
        ):
            self.bot.dispatch(
                Event.SEASON_STOP,
                SeasonEndPayload.create(
                    guild_id=guild_id,
                    season=season,
                    ranked_players=ranked_players,
                ),
            )

    @app_commands.command(
        name="list",
        description="List information about all current and previous seasons",
    )
    async def _list_season(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert (guild_id := interaction.guild_id) is not None

        seasons = await self.bot.stats_manager.get_all_seasons(guild_id)

        seasons_list_view = SeasonsListView(
            source_interaction=interaction,
            seasons=seasons,
        )
        seasons_list_view.init_components()

        await interaction.response.send_message(view=seasons_list_view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SeasonCog(bot))
