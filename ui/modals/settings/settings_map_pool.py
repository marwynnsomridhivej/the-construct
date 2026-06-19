import traceback
from typing import List

import discord

from canned import Canned
from exceptions import InvalidMapPoolName
from matchmanager import R6_QUICKMATCH, R6Map
from settingsmanager import PER_MAP_POOL_LIMIT, DEFAULT_MAP_POOL_NAMES, CustomMapPool

__all__ = (
    "SettingsMapPoolCreateModal",
    "SettingsMapPoolEditModal",
)


class SettingsMapPoolCreateModal(discord.ui.Modal):
    def __init__(self, bot):
        super().__init__(title="Create Custom Map Pool")

        from bot import Bot
        self.__bot: Bot = bot

        self.is_valid = True
        self.name: str = None
        self.maps: List[R6Map] = None

        self.init_components()

    def init_components(self) -> None:
        self.name_input = discord.ui.Label(
            text="Name",
            description="Please set the desired name for this custom map pool.",
            component=discord.ui.TextInput(
                placeholder="Enter the name here",
                min_length=1,
                max_length=50,
                required=True,
            ),
        )
        self.maps_select = discord.ui.Label(
            text="Select Maps",
            description=f"Please select between 5 to {PER_MAP_POOL_LIMIT} unique maps for this custom map pool.",
            component=discord.ui.Select(
                min_values=5,
                max_values=PER_MAP_POOL_LIMIT,
                options=[
                    discord.SelectOption(
                        label=r6map.replace("_", " ").title(),
                        value=r6map.value,
                    ) for r6map in sorted(R6_QUICKMATCH)
                ],
                required=True,
            ),
        )

        for item in [self.name_input, self.maps_select]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.name_input.component, discord.ui.TextInput)
        assert isinstance(self.maps_select.component, discord.ui.Select)

        # Set name and map variables for ease of access
        self.name = self.name_input.component.value.lower()
        self.maps = [R6Map(value)
                     for value in self.maps_select.component.values]

        # Prevent using default names
        if self.name in DEFAULT_MAP_POOL_NAMES:
            raise InvalidMapPoolName(self.name)

        await interaction.response.defer()
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, InvalidMapPoolName):
            await interaction.response.send_message(Canned.ERR_SETTINGS_CREATE_MAP_POOL_NAME, ephemeral=True)
        else:
            self.__bot.logger.error(
                f"An exception occurred when creating custom map pool: {error}"
            )
            traceback.print_exception(type(error), error, error.__traceback__)
            await interaction.response.send_message(Canned.ERR_SETTINGS_CREATE_MAP_POOL, ephemeral=True)

        self.is_valid = False
        self.stop()


class SettingsMapPoolEditModal(discord.ui.Modal):
    def __init__(self, bot, previous: CustomMapPool):
        super().__init__(title="Edit Custom Map Pool")

        from bot import Bot
        self.__bot: Bot = bot

        self.previous = previous

        self.is_valid = True
        self.name: str = None
        self.maps: List[R6Map] = None

        self.init_components()

    def init_components(self) -> None:
        self.name_input = discord.ui.Label(
            text="Name",
            description="Please set the desired name for this custom map pool.",
            component=discord.ui.TextInput(
                placeholder="Enter the name here",
                min_length=1,
                max_length=50,
                default=self.previous.name,
                required=True,
            ),
        )
        self.maps_select = discord.ui.Label(
            text="Select Maps",
            description=f"Please select between 5 to {PER_MAP_POOL_LIMIT} unique maps for this custom map pool.",
            component=discord.ui.Select(
                min_values=5,
                max_values=PER_MAP_POOL_LIMIT,
                options=[
                    discord.SelectOption(
                        label=r6map.replace("_", " ").title(),
                        value=r6map.value,
                        default=r6map in self.previous.maps,
                    ) for r6map in sorted(R6_QUICKMATCH)
                ],
                required=True,
            ),
        )

        for item in [self.name_input, self.maps_select]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.name_input.component, discord.ui.TextInput)
        assert isinstance(self.maps_select.component, discord.ui.Select)

        # Set name and map variables for ease of access
        self.name = self.name_input.component.value.lower()
        self.maps = [R6Map(value)
                     for value in self.maps_select.component.values]

        # If nothing changed, make modal not valid
        if self.name == self.previous.name and sorted(self.maps) == sorted(self.previous.maps):
            self.is_valid = False

        await interaction.response.defer()
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.__bot.logger.error(
            f"An exception occurred when creating custom map pool: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)

        await interaction.response.send_message(Canned.ERR_SETTINGS_CREATE_MAP_POOL, ephemeral=True)
        self.is_valid = False
        self.stop()
