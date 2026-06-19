import traceback
from typing import List

import discord

from canned import Canned


class R6DraftModal(discord.ui.Modal):
    def __init__(self, *, view):
        super().__init__(title="Draft Player")

        from ...views import R6View
        self.r6view: R6View = view

        for item in self.init_components():
            self.add_item(item)

    def init_components(self) -> List[discord.ui.Item]:
        self.draft = discord.ui.Label(
            text="Draft Player",
            description="Select a player to draft",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(
                        label=name,
                        value=_id
                    ) for name, _id in self.r6view.draftable_players
                ],
                required=True,
            ),
        )
        return [self.draft]

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.draft.component, discord.ui.RadioGroup)

        captain_id = interaction.user.id
        drafted_id = int(self.draft.component.value)

        # Use MatchManager.draft to write to disk
        await self.r6view.bot.match_manager.draft_player(
            interaction.guild_id,
            self.r6view.payload.match_name,
            captain_id,
            drafted_id
        )

        # Update local MatchEntry instance attached to R6View
        await self.r6view.update_match()

        # Notify
        await interaction.response.send_message(f"Captain <@{captain_id}> has drafted <@{drafted_id}>", delete_after=10.0)

        # Check if there is one player left. If so, do the following actions:
        # If playercount is:
        #   EVEN    --> auto-draft to opposite side (higher elo captain)
        #   ODD     --> auto-draft to same side (lower elo captain)
        #
        # If there is more than one player left, notify the other captain they can draft.
        if len(self.r6view.draftable_players) > 1:
            await interaction.channel.send(f"*It is now <@{self.r6view.other_captain_id(captain_id)}>'s turn to draft*", delete_after=10.0)
            return

        # Last player to draft in draftable [name, id (in string form)]
        drafted_id = int(self.r6view.draftable_players[0][1])

        # Switch captain_id to the other captain if playercount is EVEN
        # Do not switch if playercount is ODD, otherwise higher elo captain is on the team +1
        if self.r6view.playercount % 2 == 0:
            captain_id = self.r6view.other_captain_id(captain_id)

        # Draft the last remaining player
        await self.r6view.bot.match_manager.draft_player(
            interaction.guild_id,
            self.r6view.payload.match_name,
            captain_id,
            drafted_id
        )

        # Update local MatchEntry instnace attached to R6View
        await self.r6view.update_match()

        # Notify
        await interaction.channel.send(f"Captain <@{captain_id}> has drafted <@{drafted_id}>", delete_after=10.0)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.r6view.bot.logger.error(
            f"An exception occurred when trying to draft player: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_R6DRAFT_GEN_DRAFT)
