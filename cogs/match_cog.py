import random
from typing import Coroutine, Dict, List, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from canned import Canned
from event import *
from exceptions import *
from matchmanager import R6_QUICKMATCH, R6_RANKED
from queuemanager import CaptSelect, QueueType
from settingsmanager import DEFAULT_MAP_POOL_NAMES, CustomMapPool
from ui import MatchStartDMView, PreMatchModal, R6View


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
        for user_id in payload.entry.players:
            user = self.bot.get_user(user_id)
            if user is None:
                continue
            try:
                message = await user.send(view=MatchStartDMView(
                    guild=self.bot.get_guild(payload.guild_id),
                    payload=payload,
                ))
                await self.bot.dm_manager.create(payload.guild_id, user_id, message.id)
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                continue

    async def _init_match_data(self, payload: PrematchPayload) -> None:
        # Correct for QueueType mismatch based on playercount
        if len(payload.entry.players) == 2:
            payload.entry.type = QueueType.R6_1V1

        await self.bot.match_manager.create_match(payload=payload)
        match = await self.bot.match_manager.get_match(payload.guild_id, payload.match_name)

        # Create thread channel
        tc = self.bot.get_channel(payload.text_channel_id)
        thread_channel = await tc.create_thread(
            name=f"{payload.match_name} - {payload.entry.type}",
        )

        # Add all bot admins and server owner to the thread
        guild = self.bot.get_guild(payload.guild_id)
        owner_id = guild.owner_id if guild is not None else None
        admin_ids = await self.bot.settings_manager.get_admins(payload.guild_id, owner_id=owner_id)
        for admin_id in admin_ids:
            user = self.bot.get_user(admin_id)
            if user is None:
                continue
            try:
                # Don't force add an admin if they are already a player
                if user.id in payload.entry.players:
                    continue
                await thread_channel.add_user(user)
            except discord.HTTPException:
                pass
            except discord.Forbidden:
                self.bot.logger.error(
                    f"Unable to add admin id {user.id} to thread_channel " +
                    f"{thread_channel.name} (id={thread_channel.id})"
                )

        # Edit in place payload text channel ID to be thread channel now
        payload.switch_to_thread_channel(thread_channel.id)

        # Initialise R6View
        r6view = R6View(payload=payload, match=match, bot=self.bot)
        await r6view.set_order()
        r6view.init_components()

        # Send R6View to thread channel
        message = await thread_channel.send(view=r6view)
        self.bot.dispatch(Event.PREMATCH_DM_READY_SEND,
                          PrematchDMPayload.from_prematch_payload(payload, message))

    async def is_admin_including_owner(self, interaction: discord.Interaction) -> bool:
        guild = self.bot.get_guild(interaction.guild_id)
        owner_id = guild.owner_id if guild is not None else None
        return owner_id == interaction.user.id or await self.bot.settings_manager.is_admin(
            interaction.guild_id,
            interaction.user.id,
        )

    async def _select_captains(self, *, guild_id: int, queue_type: QueueType, player_ids: List[int], mode: CaptSelect) -> Tuple[int, int]:
        match mode:
            case CaptSelect.RANDOM:
                return tuple(random.sample(player_ids, 2))
            case CaptSelect.RATING:
                captains = sorted([
                    await self.bot.stats_manager.get_or_create_player(
                        guild_id=guild_id,
                        queue_type=queue_type,
                        user_id=_id
                    ) for _id in player_ids
                ], key=lambda p: p.ordinal if not p.is_legacy else p.points, reverse=True)
                return (captains[0].id, captains[1].id)
            case _:
                raise ValueError(mode)

    @app_commands.command(name="start", description="Enter pre-match configuration details")
    async def _start_match(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        owner_id = interaction.user.id

        # Check if the guild has an active season
        try:
            await self.bot.stats_manager.ensure_season(guild_id=guild_id)
        except ValueError:
            return await interaction.response.send_message(Canned.ERR_SEASON_NO_EXISTS, ephemeral=True)

        # Check if user is bot admin or server owner
        admin_or_owner = await self.is_admin_including_owner(interaction)

        # See if the person starting the match has any queues they can start from
        owned_queues = await self.bot.queue_manager.get_queues_owned_by(
            guild_id,
            owner_id,
            admin=admin_or_owner,
        )
        valid_owned_queues = {
            name: entry for name, entry in owned_queues.items()
            if len(entry.players) >= 2
            and not entry.in_progress
        }
        if not valid_owned_queues:
            return await interaction.response.send_message(Canned.ERR_MATCH_START_QUEUES, ephemeral=True)

        # Check if a text channel has been bound
        bound_text_channel_id = await self.bot.settings_manager.get_bound_text_channel_id(interaction.guild_id)
        if bound_text_channel_id is None:
            return await interaction.response.send_message(Canned.ERR_MATCH_START_NO_TC_BOUND, ephemeral=True)

        # Check if the bound text channel is still valid
        tc = interaction.guild.get_channel(bound_text_channel_id)
        if tc is None:
            return await interaction.response.send_message(Canned.ERR_MATCH_START_INVALID_TC, ephemeral=True)

        # Get all map pools created in the guild, custom and default
        ranked_name, qm_name = DEFAULT_MAP_POOL_NAMES
        ranked_pool = CustomMapPool.create(
            self.bot.user.id, ranked_name, R6_RANKED)
        qm_pool = CustomMapPool.create(
            self.bot.user.id, qm_name, R6_QUICKMATCH)
        all_pools = [ranked_pool, qm_pool] + await self.bot.settings_manager.get_all_map_pools(interaction.guild_id)

        # If previous checks succeed, display the prematch modal
        prematch_modal = PreMatchModal(self.bot, valid_owned_queues, all_pools)
        await interaction.response.send_modal(prematch_modal)

        # Ensure we don't access any attributes until user has submitted
        await prematch_modal.wait()

        # Don't do anything if we get an invalid answer or the modal errored out
        if not prematch_modal.is_valid:
            return

        # Check if our entry can be started
        assert isinstance(prematch_modal.queue.component, discord.ui.Select)
        name: str = prematch_modal.queue.component.values[0]
        try:
            entry = await self.bot.queue_manager.start_match(guild_id, owner_id, name, admin=admin_or_owner)
        except QueueProgressStateError:
            await interaction.followup.send(Canned.ERR_MATCH_IN_PROGRESS, ephemeral=True)

        # For type hints
        assert isinstance(prematch_modal.vc.component,
                          discord.ui.ChannelSelect)
        assert isinstance(prematch_modal.map_pool.component, discord.ui.Select)
        assert isinstance(
            prematch_modal.captain_select.component, discord.ui.RadioGroup)
        assert isinstance(
            prematch_modal.manual_select.component, discord.ui.UserSelect)

        vc = prematch_modal.vc.component.values[0]

        # Get map pool instance from name
        pool_name = prematch_modal.map_pool.component.values[0]
        map_pool = ranked_pool if pool_name == ranked_name else \
            qm_pool if pool_name == qm_name else \
            await self.bot.settings_manager.get_map_pool(guild_id, pool_name)

        # Craft payload to be dispatched on event
        mode = prematch_modal.captain_select.component.value
        if mode == CaptSelect.MANUAL:
            captains = tuple(
                userlike.id for userlike in prematch_modal.manual_select.component.values
            )
        else:
            captains = await self._select_captains(
                guild_id=guild_id,
                queue_type=entry.type,
                player_ids=entry.players,
                mode=mode
            )
        payload = PrematchPayload.parse({
            "guild_id": guild_id,
            "match_name": name,
            "voice_channel_id": vc.id,
            "text_channel_id": tc.id,
            "map_pool": map_pool.serialise(),
            "captains": captains,
            "entry": entry,
        })

        # Confirmation message and event dispatch
        await interaction.followup.send(Canned.MATCH_DM_CONF, ephemeral=True)
        self.bot.dispatch(Event.PREMATCH_MODAL_DONE, payload)


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
