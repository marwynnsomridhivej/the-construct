from itertools import combinations
from typing import Coroutine, Dict, List, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from canned import Canned
from event import AutoDraftPayload, Event, PrematchDMPayload, PrematchPayload
from matchmanager import R6_QUICKMATCH, R6_RANKED
from queuemanager import QueueType
from settingsmanager import DEFAULT_MAP_POOL_NAMES, CustomMapPool
from ui import MatchStartDMView, PrematchView, PrematchViewButtons, R6View


@app_commands.guild_only()
class MatchCog(commands.GroupCog, name="match"):
    def __init__(self, bot):
        from bot import Bot

        self.bot: Bot = bot

    async def cog_load(self):
        _handlers: Dict[Coroutine, Event] = {
            self._init_match_data: Event.PREMATCH_MODAL_DONE,
            self._prematch_dm: Event.PREMATCH_DM_READY_SEND,
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[MatchCog] Successfully loaded")

    async def _prematch_dm(self, payload: PrematchDMPayload) -> None:
        for user_id in payload.queue_entry.players:
            user = self.bot.get_user(user_id)
            if user is None:
                continue
            try:
                message = await user.send(
                    view=MatchStartDMView(
                        guild=self.bot.get_guild(payload.guild_id),
                        payload=payload,
                    )
                )
                await self.bot.dm_manager.create(payload.guild_id, user_id, message.id)
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                continue

    async def _perform_auto_draft(
        self, payload: PrematchPayload
    ) -> Tuple[Tuple[int, int], Tuple[List[int], List[int]]]:
        players = [
            await self.bot.stats_manager.get_or_create_player(
                guild_id=payload.guild_id,
                queue_type=payload.queue_entry.type,
                user_id=player_id,
            )
            for player_id in payload.queue_entry.players
        ]

        best_delta = 1
        most_balanced_teams = None

        # Brute force search for most balanced team composition using OpenSkill
        for team_a_players in combinations(players, len(players) // 2):
            team_b_players = [
                player for player in players if player not in team_a_players
            ]
            teams = [
                [
                    self.bot.stats_manager.model.create_rating(
                        [player.mu, player.sigma],
                        name=str(player.id),
                    )
                    for player in team_players
                ]
                for team_players in (team_a_players, team_b_players)
            ]

            # Predict the win probability (closer to 0.5, the better)
            odds_a, odds_b = self.bot.stats_manager.model.predict_win(teams)
            delta = abs(odds_a - odds_b)

            # Save the team configuration that is predicted to be the most even
            if delta < best_delta:
                best_delta = delta
                most_balanced_teams = [
                    [
                        int(player.name)
                        for player in sorted(
                            team,
                            key=lambda p: p.ordinal(),
                            reverse=True,
                        )
                    ]
                    for team in teams
                ]

        # Isolate captains and non-captains
        captains = tuple([team[0] for team in most_balanced_teams])
        non_captains = tuple([team[1:] for team in most_balanced_teams])

        return (captains, non_captains)

    async def _init_match_data(self, payload: PrematchPayload) -> None:
        # Correct for QueueType mismatch based on playercount
        if len(payload.queue_entry.players) == 2:
            payload.queue_entry.type = QueueType.R6_1V1

        # Create autodraft payload if autodraft is enabled
        auto_draft = None
        if payload.auto_draft and len(payload.queue_entry.players) > 2:
            auto_draft = AutoDraftPayload.create(
                *await self._perform_auto_draft(payload)
            )

        # Create match instance and attach it to the PrematchPayload
        await self.bot.match_manager.create_match(
            payload=payload, auto_draft=auto_draft
        )
        match = await self.bot.match_manager.get_match(
            payload.guild_id, payload.match_name
        )
        payload.attach_match_entry(match)

        # Create thread channel
        tc = self.bot.get_channel(payload.text_channel_id)
        thread_channel = await tc.create_thread(
            name=f"{payload.match_name} - {payload.queue_entry.type}",
        )

        # Add all bot admins and server owner to the thread
        guild = self.bot.get_guild(payload.guild_id)
        owner_id = guild.owner_id if guild is not None else None
        admin_ids = await self.bot.settings_manager.get_admins(
            payload.guild_id, owner_id=owner_id
        )
        for admin_id in admin_ids:
            user = self.bot.get_user(admin_id)
            if user is None:
                continue
            try:
                # Don't force add an admin if they are already a player
                if user.id in payload.queue_entry.players:
                    continue
                await thread_channel.add_user(user)
            except discord.HTTPException:
                pass
            except discord.Forbidden:
                self.bot.logger.error(
                    f"Unable to add admin id {user.id} to thread_channel "
                    + f"{thread_channel.name} (id={thread_channel.id})"
                )

        # Edit in place payload text channel ID to be thread channel now
        payload.switch_to_thread_channel(thread_channel.id)

        # Initialise R6View
        r6view = R6View(payload=payload, match=match, bot=self.bot)
        await r6view.set_order()
        await r6view.init_components()

        # Send R6View to thread channel
        message = await thread_channel.send(view=r6view)
        self.bot.dispatch(
            Event.PREMATCH_DM_READY_SEND,
            PrematchDMPayload.from_prematch_payload(payload, message),
        )

    async def is_admin_including_owner(self, interaction: discord.Interaction) -> bool:
        guild = self.bot.get_guild(interaction.guild_id)
        owner_id = guild.owner_id if guild is not None else None
        return (
            owner_id == interaction.user.id
            or await self.bot.settings_manager.is_admin(
                interaction.guild_id,
                interaction.user.id,
            )
        )

    @app_commands.command(
        name="start", description="Enter pre-match configuration details"
    )
    async def _start_match(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        owner_id = interaction.user.id

        # Check if the guild has an active season
        try:
            await self.bot.stats_manager.ensure_season(guild_id=guild_id)
        except ValueError:
            return await interaction.response.send_message(
                Canned.ERR_SEASON_NO_EXISTS, ephemeral=True
            )

        # Check if user is bot admin or server owner
        admin_or_owner = await self.is_admin_including_owner(interaction)

        # See if the person starting the match has any queues they can start from
        owned_queues = await self.bot.queue_manager.get_queues_owned_by(
            guild_id,
            owner_id,
            admin=admin_or_owner,
        )
        valid_owned_queues = {
            name: entry
            for name, entry in owned_queues.items()
            if len(entry.players) >= 2 and not entry.in_progress
        }
        if not valid_owned_queues:
            return await interaction.response.send_message(
                Canned.ERR_MATCH_START_QUEUES, ephemeral=True
            )

        # Check if a text channel has been bound
        bound_text_channel_id = (
            await self.bot.settings_manager.get_bound_text_channel_id(
                interaction.guild_id
            )
        )
        if bound_text_channel_id is None:
            return await interaction.response.send_message(
                Canned.ERR_MATCH_START_NO_TC_BOUND, ephemeral=True
            )

        # Check if the bound text channel is still valid
        tc = interaction.guild.get_channel(bound_text_channel_id)
        if tc is None:
            return await interaction.response.send_message(
                Canned.ERR_MATCH_START_INVALID_TC, ephemeral=True
            )

        # Get all map pools created in the guild, custom and default
        ranked_name, qm_name = DEFAULT_MAP_POOL_NAMES
        ranked_pool = CustomMapPool.create(self.bot.user.id, ranked_name, R6_RANKED)
        qm_pool = CustomMapPool.create(self.bot.user.id, qm_name, R6_QUICKMATCH)
        all_pools = [
            ranked_pool,
            qm_pool,
        ] + await self.bot.settings_manager.get_all_map_pools(interaction.guild_id)

        # Initialise prematch view and submit buttons
        prematch_view = PrematchView(self.bot, valid_owned_queues, all_pools)
        prematch_view_submit_button = PrematchViewButtons(
            view=prematch_view,
            original_interaction=interaction,
            admin_or_owner=admin_or_owner,
        )
        prematch_view.init_components(prematch_view_submit_button)

        # Send prematch view to user
        return await interaction.response.send_message(
            view=prematch_view, ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
