from __future__ import annotations

import random
from typing import TYPE_CHECKING, Dict, List, Tuple, Union

import discord

from canned import Canned
from event import Event, MatchPayload
from exceptions import QueueProgressStateError
from queuemanager import ALL_CAPT_SELECT_MODES, CaptSelect, QueueEntry, QueueType
from settingsmanager import DEFAULT_MAP_POOL_NAMES, CustomMapPool, MapPoolName
from statsmanager import StatsPlayer
from util import ephemeral

if TYPE_CHECKING:
    from bot import Bot

__all__ = (
    "PrematchView",
    "PrematchViewButtons",
)


class PrematchView(discord.ui.LayoutView):
    def __init__(self, bot, queues: Dict[str, QueueEntry], pools: List[CustomMapPool]):
        super().__init__(timeout=None)

        self.queues = queues
        self.pools = pools
        self.bot: Bot = bot

        # Component attributes
        self.queue_select: discord.ui.Select
        self.vc_select: discord.ui.ChannelSelect
        self.map_pool_select: discord.ui.Select
        self.auto_draft_select: discord.ui.Select
        self.captain_mode_select: discord.ui.Select
        self.captain_manual_select: discord.ui.UserSelect

        # Button actionrow
        self.button_initialised: bool = False
        self.submit_button: "PrematchViewButtons"

    @property
    def queue(self) -> Union[str, None]:
        return self.queue_select.values[0] if self.queue_select.values else None

    @property
    def voice_channel_id(self) -> Union[int, None]:
        return self.vc_select.values[0].id if self.vc_select.values else None

    @property
    def map_pool_name(self) -> Union[str, None]:
        return (
            self.map_pool_select.values[0]
            if self.map_pool_select.values
            else DEFAULT_MAP_POOL_NAMES[0]
        )

    @property
    def auto_draft(self) -> bool:
        return (
            self.auto_draft_select.values[0] == "yes"
            if self.auto_draft_select.values
            else False
        )

    @property
    def captain_mode(self) -> Union[str, None]:
        return (
            self.captain_mode_select.values[0]
            if self.captain_mode_select.values
            else ALL_CAPT_SELECT_MODES[0]
        )

    @property
    def manual_captain(self) -> List[Union[discord.Member, discord.User]]:
        return self.captain_manual_select.values

    def init_components(self, submit_button: "PrematchViewButtons") -> None:
        self.submit_button = submit_button

        # Each element of items is a dict in the format
        # {
        #   text: str
        #   description: str,
        #   component: type[discord.ui.Item],
        # }
        items = []

        # Wrap all components in here
        container = discord.ui.Container(accent_color=discord.Color.blurple())

        # Queue select
        self.queue_select = discord.ui.Select(
            options=[
                discord.SelectOption(label=name, value=name)
                for name in self.queues.keys()
            ],
            placeholder="Select queue",
        )
        items.append(
            {
                "text": "Select Queue",
                "description": "For which queue would you like to start a match?",
                "component": self.queue_select,
            }
        )

        # VC select
        self.vc_select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.voice],
            placeholder="Select voice channel",
        )
        items.append(
            {
                "text": "Voice Channel",
                "description": "What voice channel should players connec to BEFORE team draft occurs?",
                "component": self.vc_select,
            }
        )

        # Map pool select
        self.map_pool_select = discord.ui.Select(
            options=[
                discord.SelectOption(
                    label=pool.name.title(),
                    value=pool.name,
                    default=pool.name == DEFAULT_MAP_POOL_NAMES[0],
                )
                for pool in self.pools
            ],
        )
        items.append(
            {
                "text": "Map Pool",
                "description": "What map pool should this match select maps from?",
                "component": self.map_pool_select,
            }
        )

        # Autodraft toggle
        self.auto_draft_select = discord.ui.Select(
            options=[
                discord.SelectOption(
                    label=choice.title(),
                    value=choice,
                    default=choice == "no",
                )
                for choice in ["yes", "no"]
            ],
        )
        items.append(
            {
                "text": "Auto Draft",
                "description": "Should the bot automatically find the most balanced teams based on rating?",
                "component": self.auto_draft_select,
            }
        )

        # Captain selection mode select
        self.captain_mode_select = discord.ui.Select(
            options=[
                discord.SelectOption(
                    label=mode.title(),
                    value=mode,
                    default=mode == ALL_CAPT_SELECT_MODES[0],
                )
                for mode in ALL_CAPT_SELECT_MODES
            ],
        )
        items.append(
            {
                "text": "Captain Selection Mode",
                "description": "How should captain selection occur?",
                "component": self.captain_mode_select,
            }
        )

        # Manual captain select
        self.captain_manual_select = discord.ui.UserSelect(
            min_values=2,
            max_values=2,
            placeholder="Select users if manually selection captains",
        )
        items.append(
            {
                "text": "Manual Captain Selection",
                "description": "If the captain selection mode is manual, which two players should be team captains?",
                "component": self.captain_manual_select,
            }
        )

        # Add fixed header section
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "\n".join(
                        [
                            "## Match Configuration",
                            "You are able to configure certain aspects of the match here. "
                            + "Once finished, please click the *`Submit`* button below.",
                        ]
                    )
                ),
                accessory=discord.ui.Thumbnail(self.bot.user.avatar.url),
            )
        )
        container.add_item(discord.ui.Separator(visible=False))

        # Add the rest of the items to container according to data provided
        for data in items:
            for item in self.generate_label(**data):
                if item.type == discord.ComponentType.text_display:
                    container.add_item(item)
                else:
                    container.add_item(discord.ui.ActionRow(item))
            container.add_item(
                discord.ui.Separator(
                    visible=False, spacing=discord.SeparatorSpacing.large
                )
            )

        # Add the submit button
        container.add_item(self.submit_button)

        # Add container to the view
        self.add_item(container)

    def generate_label(
        self, *, text: str, description: str, component: discord.ui.Item
    ) -> List[type[discord.ui.Item]]:
        component.callback = self.generic_callback
        return [
            discord.ui.TextDisplay(
                "\n".join(
                    [
                        f"### {text}",
                        description,
                    ]
                )
            ),
            component,
        ]

    async def generic_callback(self, interaction: discord.Interaction) -> None:
        return await interaction.response.defer()


class PrematchViewButtons(discord.ui.ActionRow):
    def __init__(
        self,
        *,
        view: PrematchView,
        original_interaction: discord.Interaction,
        admin_or_owner: bool,
    ):
        super().__init__()
        self.parent_view = view
        self.original_interaction = original_interaction
        self.admin_or_owner = admin_or_owner

        self.submit_button = discord.ui.Button(
            label="Submit", style=discord.ButtonStyle.blurple
        )
        self.submit_button.callback = self.submit_button_callback
        self.add_item(self.submit_button)

        self.cancel_button = discord.ui.Button(
            label="Cancel", style=discord.ButtonStyle.danger
        )
        self.cancel_button.callback = self.cancel_button_callback
        self.add_item(self.cancel_button)

    async def select_captains(
        self,
        *,
        guild_id: int,
        queue_type: QueueType,
        player_ids: List[int],
        mode: CaptSelect,
    ) -> Tuple[int, int]:
        match mode:
            case CaptSelect.RANDOM:
                return tuple(random.sample(player_ids, 2))
            case CaptSelect.RATING:
                captains: List[StatsPlayer] = sorted(
                    [
                        await self.parent_view.bot.stats_manager.get_or_create_player(
                            guild_id=guild_id, queue_type=queue_type, user_id=_id
                        )
                        for _id in player_ids
                    ],
                    key=lambda p: p.ordinal if not p.is_legacy else p.points,
                    reverse=True,
                )
                return (captains[0].id, captains[1].id)
            case _:
                raise ValueError(mode)

    async def submit_button_callback(self, interaction: discord.Interaction) -> None:

        # Check if a queue has been specified
        if self.parent_view.queue is None:
            return await interaction.response.send_message(
                Canned.ERR_PREMATCH_NO_QUEUE, **ephemeral()
            )

        # Check if a voice channel has been selected
        if self.parent_view.voice_channel_id is None:
            return await interaction.response.send_message(
                Canned.ERR_PREMATCH_NO_VC, **ephemeral()
            )

        # Check if manual captain select was filled correctly
        if self.parent_view.captain_mode == CaptSelect.MANUAL:
            # Ensure only two users were selected
            if len(self.parent_view.manual_captain) != 2:
                return await interaction.response.send_message(
                    Canned.ERR_PREMATCH_MANUAL_CAPTAIN, **ephemeral()
                )

            # Ensure no bots in selected users
            if any([user.bot for user in self.parent_view.manual_captain]):
                return await interaction.response.send_message(
                    Canned.ERR_PREMATCH_BOT_USER, **ephemeral()
                )

            # Ensure the users selected are in the player pool
            player_ids = self.parent_view.queues[self.parent_view.queue].players
            if not all(
                [user.id in player_ids for user in self.parent_view.manual_captain]
            ):
                return await interaction.response.send_message(
                    Canned.ERR_PREMATCH_INVALID_USER, **ephemeral()
                )

        # Check if a text channel has been bound
        bound_text_channel_id = (
            await self.parent_view.bot.settings_manager.get_bound_text_channel_id(
                interaction.guild_id
            )
        )
        if bound_text_channel_id is None:
            return await interaction.response.send_message(
                Canned.ERR_MATCH_START_NO_TC_BOUND, **ephemeral()
            )

        # Check if the bound text channel exists
        bound_text_channel = interaction.guild.get_channel(bound_text_channel_id)
        if bound_text_channel is None:
            return await interaction.response.send_message(
                Canned.ERR_MATCH_START_INVALID_TC, **ephemeral()
            )

        # Check if the bot can send messages in the bound text channel
        bot_member = interaction.guild.get_member(self.parent_view.bot.user.id)
        can_send_messages_in_threads = (
            bound_text_channel.permissions_for(bot_member).send_messages_in_threads
            if bot_member
            else False
        )
        if not can_send_messages_in_threads:
            return await interaction.response.send_message(
                Canned.ERR_MATCH_START_TC_PERMS, **ephemeral()
            )

        # Check if the queue entry can be started
        try:
            if self.parent_view.queue is not None:
                queue_entry = await self.parent_view.bot.queue_manager.start_match(
                    interaction.guild_id,
                    interaction.user.id,
                    self.parent_view.queue,
                    admin=self.admin_or_owner,
                )
        except QueueProgressStateError:
            return await interaction.response.send_message(
                Canned.ERR_MATCH_IN_PROGRESS, **ephemeral()
            )

        # Delete the original message if all checks passed
        await self.original_interaction.delete_original_response()

        # Get map pool from specified name
        match self.parent_view.map_pool_name:
            case MapPoolName.RANKED:
                map_pool = self.parent_view.pools[0]
            case MapPoolName.QUICKMATCH:
                map_pool = self.parent_view.pools[1]
            case _:
                map_pool = await self.parent_view.bot.settings_manager.get_map_pool(
                    interaction.guild_id, self.parent_view.map_pool_name
                )

        # Get captains based on select mode
        if self.parent_view.captain_mode == CaptSelect.MANUAL:
            captains = tuple(user.id for user in self.parent_view.manual_captain)
        else:
            captains = await self.select_captains(
                guild_id=interaction.guild_id,
                queue_type=queue_entry.type,
                player_ids=queue_entry.players,
                mode=self.parent_view.captain_mode,
            )

        # Craft MatchPayload
        payload = MatchPayload.parse(
            {
                "guild_id": interaction.guild_id,
                "match_name": self.parent_view.queue,
                "voice_channel_id": self.parent_view.voice_channel_id,
                "text_channel_id": bound_text_channel_id,
                "map_pool": map_pool.serialise(),
                "auto_draft": self.parent_view.auto_draft,
                "captains": captains,
                "queue_entry": queue_entry.serialise(),
                "match_entry": None,
            }
        )

        # Dispatch PREMATCH_MODAL_DONE and send confirmation message
        await interaction.response.send_message(
            Canned.MATCH_DM_CONF, **ephemeral(seconds=10)
        )
        self.parent_view.bot.dispatch(Event.PREMATCH_MODAL_DONE, payload)

    async def cancel_button_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await self.original_interaction.delete_original_response()
