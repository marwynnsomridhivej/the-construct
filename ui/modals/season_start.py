import traceback
from typing import Union

import discord

from canned import Canned

__all__ = ("SeasonStartModal",)


class SeasonStartModal(discord.ui.Modal):
    def __init__(self, *, bot):
        super().__init__(title="Start Season")

        from bot import Bot

        self.bot: Bot = bot

        # Check this for the finalised name
        self.name: Union[str, None] = None

        self.init_components()

    def init_components(self) -> None:
        self.season_name = discord.ui.Label(
            text="Season Name",
            description="Please enter the name you would like to use for the season",
            component=discord.ui.TextInput(
                style=discord.TextStyle.short,
                min_length=4,
                max_length=50,
            ),
        )

        self.add_item(self.season_name)

    async def on_submit(self, interaction: discord.Interaction):
        # This modal should not send any actual response
        await interaction.response.defer()

        # Type hints
        assert isinstance(self.season_name.component, discord.ui.TextInput)

        self.name = self.season_name.component.value.lower()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.bot.logger.error(
            f"An exception occurred when trying to start a season: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(Canned.ERR_SEASON_GEN_START)
