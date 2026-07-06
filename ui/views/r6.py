from __future__ import annotations

import random
import traceback
from decimal import Decimal
from typing import TYPE_CHECKING

import discord

from canned import Canned
from event import (
    DMDeletePayload,
    Event,
    MatchFinalisedPayload,
    MatchPayload,
    Reason,
    VCResetPayload,
)
from matchmanager import MatchEntry, MatchTeam, R6Map
from queuemanager import QueueType
from statsmanager import StatsPlayer
from util import ICON, ephemeral, titlecase

from ..modals import (
    ConfirmationModal,
    R6DraftModal,
    R6MapBanModal,
    R6MVPModal,
    R6ResultModal,
    R6SideModal,
)

if TYPE_CHECKING:
    from bot import Bot

__all__ = (
    "R6View",
    "R6ViewButtons",
    "R6ViewAdminButtons",
)

INIT_DISABLED = [
    "Ban Map",
    "Side Select",
    "Designate MVP",
    "Report Results",
]
INIT_DISABLED_1V1 = [
    "Draft Player",
    "Side Select",
    "Designate MVP",
    "Report Results",
]


class R6ViewButtons(discord.ui.ActionRow):
    def __init__(self, *, view: "R6View"):
        super().__init__()
        self.r6view = view

        # Draft Index
        self.index: dict[str, int]

        # Initialise everything to starting states
        self.reset_to_default_state()

    def increment_index(self, index: str) -> None:
        self.index[index] += 1
        self.index[index] %= 2

    async def disable_button(
        self, interaction: discord.Interaction, *, label: str, disabled: bool
    ) -> None:
        button = None
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == label:
                button = child
                break
        else:
            return

        if button.disabled != disabled:
            assert interaction.message is not None

            button.disabled = disabled
            await interaction.message.edit(view=self.r6view)

    def reset_to_default_state(self) -> None:
        """Sets all buttons to their default fresh state.

        Note: This does NOT automatically update the view.
        """
        items = INIT_DISABLED_1V1 if self.r6view.should_reset_draft else INIT_DISABLED
        for child in self.children:
            if not isinstance(child, discord.ui.Button):
                continue

            if child.label in items:
                child.disabled = True
            else:
                child.disabled = False

        # Initialise draft and ban indices to zero
        self.index = {
            "draft": 0,
            "ban": 0,
        }

    def is_captain(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in self.r6view.match.captains

    async def can_interact(self, interaction: discord.Interaction) -> bool:
        assert interaction.guild_id is not None
        assert interaction.guild is not None

        # Let the user interact if they are:
        #   - A captain of a team
        #   - A designated bot admin
        #   - The server owner
        return (
            self.is_captain(interaction)
            or await self.r6view.bot.settings_manager.is_admin(
                interaction.guild_id, interaction.user.id
            )
            or interaction.guild.owner_id == interaction.user.id
        )

    async def can_admin_interact(self, interaction: discord.Interaction) -> bool:
        assert interaction.guild_id is not None
        assert interaction.guild is not None

        # Let the user interact if they are:
        #   - The queue owner
        #   - A designated bot admin
        #   - The server owner
        #
        # Captainship is not a sufficient criteria for actions with elevated permission
        return (
            self.is_queue_owner(interaction)
            or await self.r6view.bot.settings_manager.is_admin(
                interaction.guild_id, interaction.user.id
            )
            or interaction.guild.owner_id == interaction.user.id
        )

    def is_queue_owner(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.r6view.payload.queue_entry.owner_id

    async def reset_to_default(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None
        assert interaction.message is not None

        channel = interaction.channel
        assert isinstance(channel, discord.Thread)

        await self.r6view.bot.match_manager.reset_draft(
            interaction.guild_id, self.r6view.payload
        )
        await self.r6view.update_match()
        await channel.send(
            content="Player draft, map bans, and starting side selection have been reset",
            delete_after=10.0,
        )

        # Set view buttons to default state
        self.reset_to_default_state()
        await interaction.message.edit(view=self.r6view)

    async def cancel(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None

        # Delete match entry
        await self.r6view.bot.match_manager.delete_match(
            interaction.guild_id, self.r6view.payload.match_name
        )

        # Set in_progress to False
        await self.r6view.bot.queue_manager.set_progress_state(
            interaction.guild_id,
            self.r6view.payload.match_name,
            False,
        )

        # Unlock queue
        await self.r6view.bot.queue_manager.set_queue_lock_state(
            interaction.guild_id,
            interaction.user.id,
            self.r6view.payload.match_name,
            False,
            admin=await self.can_admin_interact(interaction),
        )

        # Mark canceled and stop listening to events
        self.r6view.match_canceled = True
        self.r6view.stop()

        # Dispatch DM_DELETE event
        self.r6view.bot.dispatch(
            Event.PREMATCH_DM_DELETE,
            DMDeletePayload.create(
                guild_id=interaction.guild_id,
                players=self.r6view.payload.queue_entry.players,
            ),
        )

    @discord.ui.button(label="Draft Player", style=discord.ButtonStyle.green)
    async def _draft_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Only let team captains successfully interact
        if not self.is_captain(interaction):
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_CAPTAIN, **ephemeral()
            )

        # Check to ensure the player interacting with this button is the one that should be drafting
        if self.r6view.current_drafting_captain.id != interaction.user.id:
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_DRAFT_TURN, **ephemeral()
            )

        # Get other team
        other_team = self.r6view.match.get_team_of_user(
            self.r6view.other_captain_id(interaction.user.id)
        )

        # Send draft modal
        draft_modal = R6DraftModal(view=self.r6view, other_team=other_team)
        await interaction.response.send_modal(draft_modal)

        # Wait for interaction to complete
        await draft_modal.wait()

        # Increment draft index
        self.increment_index("draft")

        # Allow the RESET button to be pressed
        await self.disable_button(interaction, label="Reset", disabled=False)

        # If draft is done:
        if self.r6view.finished_draft:
            # Set draft button state
            button.disabled = True

            # Enable the ban map button
            await self.disable_button(interaction, label="Ban Map", disabled=False)

            # Edit the view immediately, so the bot doesn't appear to freeze
            await self.r6view.update_text_content(interaction)

            # Send followup message to let players know vcs are being made
            channel = interaction.channel
            assert isinstance(channel, discord.Thread)
            await channel.send(Canned.R6DRAFT_VC_CREATION, delete_after=10)

            # Perform potentially laggy operations here
            await self.r6view.create_team_vcs()
            await self.r6view.move_to_team_vcs()
        else:
            # Only update the text on the R6View
            await self.r6view.update_text_content(interaction)

    @discord.ui.button(label="Ban Map", style=discord.ButtonStyle.red)
    async def _ban_map_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Only let team captains successfully interact
        if not self.is_captain(interaction):
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_CAPTAIN, **ephemeral()
            )

        # Draft order already initialised, can jump right in
        if self.r6view.current_map_banning_captain.id != interaction.user.id:
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_BAN_TURN, **ephemeral()
            )

        map_ban_modal = R6MapBanModal(view=self.r6view)
        await interaction.response.send_modal(map_ban_modal)
        await map_ban_modal.wait()

        # Increment ban index
        self.increment_index("ban")

        # Reset button SHOULD be allowed from draft already, but do again anyway
        await self.disable_button(interaction, label="Reset", disabled=False)

        # If map bans are done:
        if self.r6view.finished_map_bans:
            # Disable ban map button
            button.disabled = True

            # Enable side select button
            await self.disable_button(interaction, label="Side Select", disabled=False)

            # Edit the view immediately
            await self.r6view.update_text_content(interaction)

            # Announce the selected map
            channel = interaction.channel
            assert isinstance(channel, discord.Thread)
            assert self.r6view.match.map is not None
            await channel.send(
                f"The selected map is: **{titlecase(self.r6view.match.map.replace('_', ' '))}**",
                delete_after=10.0,
            )

            # Notify captain responsible for side select
            await channel.send(
                content=f"*It is now <@{self.r6view.current_map_banning_captain.id}>'s turn to choose what side their team starts on*",
                delete_after=10.0,
            )
        else:
            # Only update the text on the R6View
            await self.r6view.update_text_content(interaction)

    @discord.ui.button(label="Side Select", style=discord.ButtonStyle.blurple)
    async def _side_select_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Only let team captains successfully interact
        if not self.is_captain(interaction):
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_CAPTAIN, **ephemeral()
            )

        if self.r6view.current_map_banning_captain.id != interaction.user.id:
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_SIDE, **ephemeral()
            )

        side_modal = R6SideModal(view=self.r6view)
        await interaction.response.send_modal(side_modal)
        await side_modal.wait()

        if self.r6view.finished_side_select:
            button.disabled = True

            # Only enable MVP designation if it is not a 1v1
            if self.r6view.playercount > 2:
                await self.disable_button(
                    interaction, label="Designate MVP", disabled=False
                )

            # Enable report results regardless
            await self.disable_button(
                interaction, label="Report Results", disabled=False
            )

        # Update the text on the R6View
        await self.r6view.update_text_content(interaction)

    @discord.ui.button(label="Designate MVP", style=discord.ButtonStyle.blurple)
    async def _designate_mvp_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild_id is not None

        # Allow bot admins and team captains to interact
        if not await self.can_interact(interaction):
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_CAPTAIN, **ephemeral()
            )

        captain_id = None

        # If the user is captain, assign captain_id to the user's ID
        if self.is_captain(interaction):
            captain_id = interaction.user.id

        # Set captain_id to any captain_id for a team that has yet to designate
        # their MVP if they are an admin AND EITHER
        #   - They are not a captain (captain_id will still be None)
        #   - They are a captain AND their team already
        #     has an MVP designation (captain_id will be overwritten to the other team's captain ID)
        if await self.r6view.bot.settings_manager.is_admin(
            interaction.guild_id, interaction.user.id
        ):
            if (
                captain_id is None
                or self.r6view.match.get_team_of_user(interaction.user.id).mvp_id
                is not None
            ):
                team_awaiting_mvp = self.r6view.get_team_awaiting_mvp()
                assert team_awaiting_mvp is not None
                captain_id = team_awaiting_mvp.captain_id

        assert captain_id is not None

        mvp_modal = R6MVPModal(
            view=self.r6view,
            captain_id=captain_id,
        )
        await interaction.response.send_modal(mvp_modal)
        await mvp_modal.wait()

        # Different than others, since we want to disable this button as opposed to enable another
        if self.r6view.match.mvps_set:
            await self.disable_button(interaction, label="Designate MVP", disabled=True)

        # Update the text on the R6View
        await self.r6view.update_text_content(interaction)

        # If this action finalises the match results (win + mvp set for both teams), disable view
        if self.r6view.check_finalised():
            await self.r6view.disable_reset_buttons(interaction)

            # Dispatch thread cleanup to close and lock threads
            self.r6view.bot.dispatch(Event.THREAD_CLEANUP, self.r6view.payload)

    @discord.ui.button(label="Report Results", style=discord.ButtonStyle.grey)
    async def _report_results_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not await self.can_admin_interact(interaction):
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_OWNER_OR_ADMIN, **ephemeral()
            )

        result_modal = R6ResultModal(view=self.r6view)
        await interaction.response.send_modal(result_modal)
        await result_modal.wait()

        # If not valid, don't proceed
        if not result_modal.is_valid:
            return

        if self.r6view.match.wins_set:
            # Similar to Designate MVP, disable this button once winner/loser is set
            await self.disable_button(
                interaction, label="Report Results", disabled=True
            )

        # Update the text on the R6View
        await self.r6view.update_text_content(interaction)

        # If this action finalises the match results (win + mvp set for both teams), disable view
        if self.r6view.check_finalised():
            await self.r6view.disable_reset_buttons(interaction)

            # Dispatch thread cleanup to close and lock threads
            self.r6view.bot.dispatch(Event.THREAD_CLEANUP, self.r6view.payload)


class R6ViewAdminButtons(discord.ui.ActionRow):
    def __init__(self, *, view, draft_row: "R6ViewButtons"):
        super().__init__()

        self.r6view: R6View = view
        self.draft_row: R6ViewButtons = draft_row

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.grey)
    async def _reset_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild_id is not None

        if not await self.draft_row.can_admin_interact(interaction):
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_OWNER_OR_ADMIN, **ephemeral()
            )

        confirm_modal = ConfirmationModal(operation="reset")
        await interaction.response.send_modal(confirm_modal)
        await confirm_modal.wait()

        # Do not proceed unless user confirms
        if not confirm_modal.proceed:
            return

        if self.draft_row.r6view.match.finalised:
            assert interaction.message is not None

            button.disabled = True
            await interaction.message.edit(view=self.draft_row.r6view)
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_FINAL, **ephemeral()
            )

        await self.draft_row.reset_to_default(interaction)
        await self.r6view.update_text_content(interaction)

        # Dispatch event to move users back to the main vc
        self.r6view.bot.dispatch(
            Event.RESET_BUTTON_PRESSED,
            VCResetPayload.create(
                interaction.guild_id,
                self.r6view.match.voice_channel_id,
                [self.r6view.match.team_a, self.r6view.match.team_b],
                self.r6view.match.type,
            ),
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def _cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        assert interaction.guild_id is not None

        if not await self.draft_row.can_admin_interact(interaction):
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_OWNER_OR_ADMIN, **ephemeral()
            )

        confirm_modal = ConfirmationModal(operation="cancel")
        await interaction.response.send_modal(confirm_modal)
        await confirm_modal.wait()

        # Do not proceed unless user confirms
        if not confirm_modal.proceed:
            return

        if self.draft_row.r6view.match.finalised:
            assert interaction.message is not None

            button.disabled = True
            await interaction.message.edit(view=self.draft_row.r6view)
            return await interaction.response.send_message(
                Canned.ERR_R6DRAFT_FINAL, **ephemeral()
            )

        # Disable all buttons in R6ViewButtons
        for label in [
            "Draft Player",
            "Ban Map",
            "Side Select",
            "Designate MVP",
            "Report Results",
        ]:
            await self.draft_row.disable_button(interaction, label=label, disabled=True)

        # Disable all buttons in R6ViewOwnerButtons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        # Perform cancel
        await self.draft_row.cancel(interaction)

        # Update message with canceled text and buttons
        await self.r6view.update_text_content(interaction)

        # Send additional message with no pings
        await interaction.followup.send(
            f"This match `{self.r6view.payload.match_name}` has been canceled. "
            + "The queue has not been deleted and can be started again."
        )

        # Dispatch event to move users back to the main vc and delet temp ones
        self.r6view.bot.dispatch(
            Event.CANCEL_BUTTON_PRESSED,
            VCResetPayload.create(
                interaction.guild_id,
                self.r6view.match.voice_channel_id,
                self.r6view.teams,
                self.r6view.match.type,
            ),
        )

        # Dispatch event to stop monitoring R6View message
        self.r6view.bot.dispatch(
            Event.UNREGISTER_MATCH_WATCH, self.r6view.payload.r6view_message_id
        )

        # Dispatch THREAD_CLEANUP event
        self.r6view.bot.dispatch(Event.THREAD_CLEANUP, self.r6view.payload)


class R6View(discord.ui.LayoutView):
    def __init__(self, *, payload: MatchPayload, match: MatchEntry, bot):
        super().__init__(timeout=None)
        self.payload = payload
        self.match = match
        self.bot: Bot = bot
        self.match_canceled = False

        # Attribute type hints
        self.map_pool: list[R6Map]
        self.map_pool_name: str

        # View components
        self.about_text: discord.ui.TextDisplay
        self.thumbnail: discord.ui.Thumbnail
        self.section: discord.ui.Section
        self.view_buttons: R6ViewButtons
        self.r6_view_admin_buttons: R6ViewAdminButtons

        # Drafting
        self.draft_order: list[StatsPlayer]
        self.op_draft_order: list[StatsPlayer]

    @property
    def teams(self) -> list[MatchTeam]:
        return [self.match.team_a, self.match.team_b]

    @property
    def current_drafting_captain(self) -> StatsPlayer:
        return self.draft_order[self.view_buttons.index["draft"]]

    @property
    def current_map_banning_captain(self) -> StatsPlayer:
        return self.op_draft_order[self.view_buttons.index["ban"]]

    @property
    def finished_draft(self) -> bool:
        return not bool(self.draftable_players)

    @property
    def finished_map_bans(self) -> bool:
        return self.match.has_map

    @property
    def finished_side_select(self) -> bool:
        return self.match.sides_selected

    @property
    def playercount(self) -> int:
        return len(self.payload.queue_entry.players)

    @property
    def draftable_players(self) -> list[tuple[str, str]]:
        # Get special 1v1 and autodraft cases out of the way
        if self.match.type == QueueType.R6_1V1 or self.payload.auto_draft:
            return []

        guild = self.bot.get_guild(self.payload.guild_id)
        if guild is None:
            raise ValueError

        # [(player displayname, str(player id)), ...]
        return [
            (
                member.display_name,
                str(_id),
            )
            for _id in self.payload.queue_entry.players
            if (member := guild.get_member(_id)) is not None
            and _id not in self.match.team_a.players
            and _id not in self.match.team_b.players
        ]

    @property
    def should_reset_draft(self) -> bool:
        return self.payload.auto_draft or self.match.type == QueueType.R6_1V1

    async def init_components(self) -> None:
        # Pick up to 7 maps from the given map pool
        self.map_pool = sorted(
            random.sample(
                self.payload.map_pool.maps, k=min(len(self.payload.map_pool), 7)
            )
        )

        # Save map pool name for display
        self.map_pool_name = titlecase(self.payload.map_pool.name)

        # Initialise buttons first, as main text depends on referencing
        # the class index attribute
        self.view_buttons = R6ViewButtons(view=self)
        self.r6_view_admin_buttons = R6ViewAdminButtons(
            view=self, draft_row=self.view_buttons
        )

        # Initialise main text section with thumbnail
        self.about_text = discord.ui.TextDisplay(await self.get_text_content())
        self.thumbnail = discord.ui.Thumbnail(media=ICON)
        self.section = discord.ui.Section(self.about_text, accessory=self.thumbnail)

        # Initialise container and put everything inside in order
        container = discord.ui.Container(
            self.section,
            self.view_buttons,
            self.r6_view_admin_buttons,
            accent_color=discord.Color.blurple(),
        )
        self.add_item(container)

    async def set_order(self) -> None:
        #   sorted() will sort ascending by default (low to high)
        #
        #   DO NOT REVERSE (we want lower points in index 0)
        #   For EVEN number of players in lobby:
        #       Player Draft    --> LOWEST points goes first
        #       Map Ban         --> HIGHEST points bans first
        #       Starting Side   --> HIGHEST points goes first (use draft[0])
        #
        #   REVERSE (we want higher points in index 0)
        #   For ODD number of players in lobby:
        #       Player Draft    --> -1 goes first (HIGHEST points)
        #       Map Ban         --> -1 goes first (HIGHEST points)
        #       Starting Side   --> -1 goes first (HIGHEST points)
        self.draft_order = sorted(
            [
                await self.bot.stats_manager.get_or_create_player(
                    guild_id=self.payload.guild_id,
                    queue_type=self.payload.queue_entry.type,
                    user_id=_id,
                )
                for _id in self.match.captains
            ],
            key=lambda p: p.ordinal if not p.is_legacy else float(p.points or 0),
            reverse=bool(self.playercount % 2),
        )

        # Reverse the draft order IF there is an EVEN number of players (true opposite)
        # Otherwise, keep it same as draft order.
        #
        # If it is a 1v1, also keep it the same as draft order
        self.op_draft_order = (
            [self.draft_order[1], self.draft_order[0]]
            if (self.playercount % 2 == 0 and self.playercount > 2)
            else self.draft_order
        )

    async def get_win_chance(self, name: str) -> Decimal:
        assert self.payload.match_entry is not None

        # Convert player IDs to StatsPlayer instances
        teams: list[list[StatsPlayer]] = [
            [
                await self.bot.stats_manager.get_or_create_player(
                    guild_id=self.payload.guild_id,
                    queue_type=self.payload.match_entry.type,
                    user_id=player_id,
                )
                for player_id in team.players
            ]
            for team in self.teams
        ]

        # Convert teams to PlacketLuce ratings
        ratings = [
            [
                self.bot.stats_manager.model.create_rating(
                    [player.mu, player.sigma], name=str(player.id)
                )
                for player in team
            ]
            for team in teams
        ]

        # Return win prediction for the team name
        return Decimal(
            self.bot.stats_manager.model.predict_win(ratings)[
                0 if name == self.match.team_a.name else 1
            ]
            * 100
        ).quantize(Decimal("0.01"))

    async def get_team_players_text(self, team: MatchTeam) -> str:
        txt = f"### Team {team.name}"
        if self.match.wins_set:
            txt += " (Win)" if team.win else " (Lose)"
        else:
            txt += f"\n-# *`{await self.get_win_chance(team.name)}%` Projected Win Probability*"
        txt += "\n" + "\n".join(
            [
                # - @Player *(captain?)* *(mvp?)*
                f"- <@{_id}>{' *(captain)*' if _id == team.captain_id else ''}{' *(mvp)*' if team.mvp_id is not None and _id == team.mvp_id else ''}"
                for _id in team.players
            ]
        )
        return txt

    async def get_text_content(self) -> str:
        items = []

        # Always put title
        view_title = f"## {self.payload.match_name.upper()} [{self.match.type.upper()}]"
        items.append(view_title)

        # If canceled, show cancellation message
        if self.match_canceled:
            items.append(Canned.R6DRAFT_MATCH_CANCEL)
            return "\n".join(items)

        # Put team roster
        team_draft = "\n".join(
            [
                await self.get_team_players_text(self.match.team_a),
                await self.get_team_players_text(self.match.team_b),
            ]
        )
        items.append(team_draft)

        # Show draft pool and pick order if not done
        if not self.finished_draft:
            # Display draft pool header with any undrafted players listed below
            draft_pool = "### Player Draft Pool\n" + "\n".join(
                [f"- <@{player_id}>" for (_, player_id) in self.draftable_players]
            )
            items.append(draft_pool)

            # Display draft pick order, with *(drafting...)* next to name of
            # the captain that is currently drafting
            draft_order = "\n".join(
                [
                    "### Player Draft Order",
                    f"1. <@{self.draft_order[0].id}>"
                    + (
                        " *(drafting...)*"
                        if self.draft_order[0].id == self.current_drafting_captain.id
                        else ""
                    ),
                    f"2. <@{self.draft_order[1].id}>"
                    + (
                        " *(drafting...)*"
                        if self.draft_order[1].id == self.current_drafting_captain.id
                        else ""
                    ),
                ]
            )
            items.append(draft_order)

        # Show map ban order if not done, otherwise show selected map
        if not self.finished_map_bans:
            # Display map ban order, with *(banning...)* next to the name of
            # the captain that is currently map banning
            ban_order = "\n".join(
                [
                    "### Map Ban Order",
                    f"1. <@{self.op_draft_order[0].id}>"
                    + (
                        " *(banning)*"
                        if self.finished_draft
                        and self.op_draft_order[0].id
                        == self.current_map_banning_captain.id
                        else ""
                    ),
                    f"2. <@{self.op_draft_order[1].id}>"
                    + (
                        " *(banning)*"
                        if self.finished_draft
                        and self.op_draft_order[1].id
                        == self.current_map_banning_captain.id
                        else ""
                    ),
                ]
            )

            # Display the 5-7 maps randomly selected from the larger map pool
            # where banned maps are denoted by strikethrough
            pool = f"### Map Pool [{self.map_pool_name}]\n" + "\n".join(
                [
                    f"- {'~~' if r6map in self.match.banned_maps else ''}{titlecase(r6map.replace('_', ' '))}{'~~' if r6map in self.match.banned_maps else ''}"
                    for r6map in self.map_pool
                ]
            )
            items.append(ban_order)
            items.append(pool)
        else:
            assert self.match.map is not None

            # Display final selected map once bans are done
            selected_map = (
                "### Selected Map\n" + f"{titlecase(self.match.map.replace('_', ' '))}"
            )
            items.append(selected_map)

        # Show who gets to select the starting side if not done, otherwise show side assignments
        if not self.finished_side_select:
            side_select = "\n".join(
                [
                    "### Starting Side Selection",
                    f"- Performed by: <@{self.op_draft_order[0].id}>",
                ]
            )
            items.append(side_select)
        else:
            assert self.match.team_a.starting_side is not None
            assert self.match.team_b.starting_side is not None

            starting_sides = "\n".join(
                [
                    "### Starting Sides",
                    f"Team A: {titlecase(self.match.team_a.starting_side)}s",
                    f"Team B: {titlecase(self.match.team_b.starting_side)}s",
                ]
            )
            items.append(starting_sides)

        # Always put disclaimer
        disclaimer = "\n" + Canned.R6DRAFT_DISCLAIMER
        items.append(disclaimer)

        return "\n".join(items)

    async def update_text_content(self, interaction: discord.Interaction) -> None:
        self.about_text.content = await self.get_text_content()
        assert interaction.message is not None
        await interaction.message.edit(view=self)

    async def create_team_vcs(self) -> None:
        parent_vc = self.bot.get_channel(self.payload.voice_channel_id)
        assert isinstance(parent_vc, discord.VoiceChannel)

        guild = self.bot.get_guild(self.payload.guild_id)
        assert guild is not None

        exclude_ids = self.match.captains + [self.payload.queue_entry.owner_id]
        for offset, team in enumerate(self.teams):
            # Create and set team voice channel if it isn't already set
            # This should not be redone after a reset
            if team.voice_channel_id is None:
                coro = (
                    parent_vc.category.create_voice_channel
                    if isinstance(parent_vc.category, discord.CategoryChannel)
                    else guild.create_voice_channel
                )
                vc = await coro(
                    name=f"{self.payload.match_name} - Team {team.name}",
                    reason=f"Automated team voice channel creation for match {self.payload.match_name}",
                    position=parent_vc.position + offset,
                )

                # Set @everyone perms to no speaking
                await vc.set_permissions(guild.default_role, speak=False)

                # Set perms for members of enemy team to not be able to join
                # Does not apply to team captains and the queue owner
                for player_id in self.payload.queue_entry.players:
                    member = guild.get_member(player_id)
                    if member is None:
                        continue

                    if player_id in exclude_ids or player_id in team.players:
                        # Allow speaking if they are a team member or captain or queue owner
                        await vc.set_permissions(member, speak=True)
                    else:
                        # Don't allow opposing team members to see the other team's channel
                        await vc.set_permissions(member, view_channel=False)

                assert team.captain_id is not None
                await self.bot.match_manager.set_team_vc(
                    self.payload.guild_id,
                    self.payload.match_name,
                    team.captain_id,
                    vc.id,
                )
                await self.update_match()

    async def move_to_team_vcs(self) -> None:
        guild = self.bot.get_guild(self.payload.guild_id)
        assert guild is not None

        for team in self.teams:
            # Try to move individual players first
            assert team.voice_channel_id is not None
            team_vc = self.bot.get_channel(team.voice_channel_id)
            if not isinstance(team_vc, discord.VoiceChannel):
                continue

            for player_id in team.players:
                try:
                    member = guild.get_member(player_id)
                    if member is None:
                        continue

                    await member.move_to(team_vc, reason=Reason.TEAM_VC)
                except discord.HTTPException:
                    pass
                except Exception as e:
                    traceback.print_exception(type(e), e, e.__traceback__)

    def get_team_awaiting_mvp(self) -> MatchTeam | None:
        for team in self.teams:
            if team.mvp_id is None:
                return team
        else:
            return None

    async def update_match(self) -> None:
        self.match = await self.bot.match_manager.get_match(
            self.payload.guild_id, self.payload.match_name
        )

    def check_finalised(self) -> bool:
        finalised_1v1 = self.playercount == 2 and self.match.wins_set
        if self.match.finalised or finalised_1v1:
            # Stop listening to events on this View
            self.stop()

            # Dispatch match finalised to teardown VCs
            self.bot.dispatch(
                Event.MATCH_FINALISED,
                MatchFinalisedPayload.create(
                    guild_id=self.payload.guild_id,
                    name=self.payload.match_name,
                    queue_type=self.match.type,
                    owner_id=self.payload.queue_entry.owner_id,
                    match_entry=self.match,
                    r6view_message_id=self.payload.r6view_message_id,
                ),
            )
            return True
        return False

    async def disable_reset_buttons(self, interaction: discord.Interaction) -> None:
        for child in self.r6_view_admin_buttons.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        assert interaction.message is not None
        await interaction.message.edit(view=self)

    def other_captain_id(self, captain_id: int) -> int:
        idx = self.match.captains.index(captain_id) - 1
        return self.match.captains[idx]
