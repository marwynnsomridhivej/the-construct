import discord

from base import SettingsBaseView


class SettingsGeneralView(SettingsBaseView):
    def __init__(self, *, guild_id: int, user_id: int, source_interaction: discord.Interaction, parent_view: discord.ui.LayoutView, bot):
        from .settings_buttons import SettingsGeneralButtons
        super().__init__(
            guild_id=guild_id,
            user_id=user_id,
            source_interaction=source_interaction,
            button_cls=SettingsGeneralButtons,
            parent_view=parent_view,
            bot=bot,
        )

    async def get_text_content(self) -> str:
        items = []

        # View header
        header = "\n".join([
            "## General Settings Configuration",
            "The configured settings for this server are detailed below.",
        ])
        items.append(header)

        # Show admins
        admins = await self.bot.settings_manager.get_admins(self.guild_id)
        admins_text = "\n".join([
            "### Bot Administrators",
            "> *Bot administrators are able to act at the same permission level as the server owner*",
            "\n".join([f"- <@{user_id}>" for user_id in admins]) if admins
            else "No bot administrators have been designated yet"
        ])
        items.append(admins_text)

        # Show bound text channel
        channel_id = await self.bot.settings_manager.get_bound_text_channel_id(self.guild_id)
        channel_id_text = "\n".join([
            "### Bound Text Channel",
            "> This channel is where match related threads will be spawneds",
            f"- <#{channel_id}>" if channel_id is not None else "No text channel has been bound yet"
        ])
        items.append(channel_id_text)

        return "\n".join(items)
