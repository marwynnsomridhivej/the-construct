from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import discord

from canned import Canned
from util import ephemeral

if TYPE_CHECKING:
    from bot import Bot

__all__ = (
    "SettingsSetAdminModal",
    "SettingsBindTextChannelModal",
)


class SettingsSetAdminModal(discord.ui.Modal):
    def __init__(self, bot: Bot, previous: list[int]):
        super().__init__(title="Set Admins")
        self.previous = previous
        self.bot = bot
        self.admins: list[int]
        self.is_valid = False

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
                    user
                    for user_id in self.previous
                    if (user := self.bot.get_user(user_id))
                ],
                required=False,
            ),
        )
        self.add_item(self.admin_select)

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.admin_select.component, discord.ui.UserSelect)

        msg = None

        if any([user.bot for user in self.admin_select.component.values]):
            msg = Canned.ERR_SETTINGS_SET_ADMIN_BOT_USER
        else:
            self.admins = [user.id for user in self.admin_select.component.values]

        if sorted(self.admins) == sorted(self.previous):
            msg = Canned.SETTINGS_SET_ADMIN_ALREADY_SET

        if msg is not None:
            await interaction.response.send_message(msg, **ephemeral())
            return

        self.is_valid = True
        await interaction.response.defer()
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.bot.logger.error(f"An exception occurred when select users: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        await interaction.response.send_message(
            Canned.ERR_SETTINGS_SET_ADMIN, **ephemeral()
        )
        self.stop()


class SettingsBindTextChannelModal(discord.ui.Modal):
    def __init__(self, bot: Bot, previous: int | None):
        super().__init__(title="Bind Text Channel")
        self.previous = previous
        self.bot = bot
        self.channel_id: int
        self.is_valid = False

        self.init_components()

    def init_components(self) -> None:
        default_text_channel = (
            self.bot.get_channel(self.previous) if self.previous is not None else None
        )

        self.channel_select = discord.ui.Label(
            text="Select Text Channel",
            description="Please select the text channel all match related threads should be created in.",
            component=discord.ui.ChannelSelect(
                channel_types=[discord.ChannelType.text],
                placeholder="Select a text channel",
                default_values=[default_text_channel]
                if isinstance(default_text_channel, discord.TextChannel)
                else discord.utils.MISSING,
                required=True,
            ),
        )
        self.add_item(self.channel_select)

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.channel_select.component, discord.ui.ChannelSelect)
        channel = self.channel_select.component.values[0]

        resolved_channel = channel.resolve()
        assert resolved_channel is not None

        assert interaction.guild is not None
        assert self.bot.user is not None

        bot_member = interaction.guild.get_member(self.bot.user.id)
        assert bot_member is not None

        msg = None

        if self.previous == channel.id:
            msg = Canned.SETTINGS_BIND_CHANNEL_ALREADY_BOUND
        elif not resolved_channel.permissions_for(bot_member).create_private_threads:
            msg = Canned.ERR_SETTINGS_BIND_CHANNEL_PERMS

        if msg is not None:
            await interaction.response.send_message(msg, **ephemeral())
            return

        self.channel_id = channel.id
        self.is_valid = True
        await interaction.response.defer()
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.bot.logger.error(f"An exception occurred when select users: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

        await interaction.response.send_message(
            Canned.ERR_SETTINGS_BIND_CHANNEL, **ephemeral()
        )
        self.stop()
