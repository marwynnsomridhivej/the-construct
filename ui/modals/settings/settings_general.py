import traceback
from typing import List

import discord

from canned import Canned

__all__ = (
    "SettingsSetAdminModal",
    "SettingsBindTextChannelModal",
)


class SettingsSetAdminModal(discord.ui.Modal):
    def __init__(self, bot, previous: List[int]):
        super().__init__(title="Set Admins")
        self.previous = previous

        from bot import Bot

        self.__bot: Bot = bot

        self.admins: List[int] = None
        self.is_valid = True

        self.init_components()

    def init_components(self) -> None:
        self.admin_select = discord.ui.Label(
            text="Select Server Members",
            description="Please select the server members you wish to grant bot admin permissions to.",
            component=discord.ui.UserSelect(
                placeholder="Select up to 5 server members",
                min_values=0,
                max_values=5,
                default_values=[
                    self.__bot.get_user(user_id) for user_id in self.previous
                ],
                required=False,
            ),
        )
        self.add_item(self.admin_select)

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.admin_select.component, discord.ui.UserSelect)
        if any([user.bot for user in self.admin_select.component.values]):
            self.is_valid = False
        else:
            self.admins = [user.id for user in self.admin_select.component.values]

        if sorted(self.admins) == sorted(self.previous):
            self.is_valid = False

        await interaction.response.defer()
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.__bot.logger.error(f"An exception occurred when select users: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        await interaction.response.send_message(
            Canned.ERR_SETTINGS_SET_ADMIN, ephemeral=True
        )
        self.is_valid = False
        self.stop()


class SettingsBindTextChannelModal(discord.ui.Modal):
    def __init__(self, bot, previous: int):
        super().__init__(title="Bind Text Channel")
        self.previous = previous

        from bot import Bot

        self.__bot: Bot = bot

        self.channel_id: int = None
        self.is_valid = True

        self.init_components()

    def init_components(self) -> None:
        self.channel_select = discord.ui.Label(
            text="Select Text Channel",
            description="Please select the text channel all match related threads should be created in.",
            component=discord.ui.ChannelSelect(
                channel_types=[discord.ChannelType.text],
                placeholder="Select a text channel",
                default_values=[self.__bot.get_channel(self.previous)]
                if isinstance(self.previous, int)
                else discord.utils.MISSING,
                required=True,
            ),
        )
        self.add_item(self.channel_select)

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.channel_select.component, discord.ui.ChannelSelect)
        channel = self.channel_select.component.values[0]
        if self.previous == channel.id:
            self.is_valid = False

        if (
            not channel.resolve()
            .permissions_for(channel.guild.get_member(self.__bot.user.id))
            .create_private_threads
        ):
            self.is_valid = False
            return await interaction.response.send_message(
                Canned.ERR_SETTINGS_BIND_CHANNEL_PERMS, ephemeral=True
            )

        self.channel_id = channel.id
        await interaction.response.defer()
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.__bot.logger.error(f"An exception occurred when select users: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        await interaction.response.send_message(
            Canned.ERR_SETTINGS_BIND_CHANNEL, ephemeral=True
        )
        self.is_valid = False
        self.stop()
