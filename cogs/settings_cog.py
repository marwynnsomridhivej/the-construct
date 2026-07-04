from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ui import SettingsSelectView
from util import EventHandlerType

if TYPE_CHECKING:
    from bot import Bot


@app_commands.guild_only()
class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot

    async def cog_load(self):
        _handlers: dict[EventHandlerType, str] = {
            self._create_settings_on_guild_join: "guild_join",
        }
        for coro, event in _handlers.items():
            self.bot.add_listener(coro, f"on_{event}")

        self.bot.logger.info("[SettingsCog] Successfully loaded")

    async def _create_settings_on_guild_join(self, guild: discord.Guild) -> None:
        # Create default settings for new guilds upon join
        await self.bot.settings_manager.create_guild_settings(guild.id)

    @app_commands.command(name="settings", description="Configure various settings")
    async def _settings(self, interaction: discord.Interaction):
        # Typehint assert, we know this is true anyway
        assert (guild_id := interaction.guild_id) is not None

        view = SettingsSelectView(
            guild_id=guild_id,
            user_id=interaction.user.id,
            source_interaction=interaction,
            bot=self.bot,
        )
        await view.init_components()
        return await interaction.response.send_message(
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot):
    await bot.add_cog(SettingsCog(bot))
