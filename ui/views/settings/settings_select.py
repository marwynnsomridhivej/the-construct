import discord

from ...urls import R6URL
from .settings_buttons import SettingsSelectButtons


class SettingsSelectView(discord.ui.LayoutView):
    def __init__(
        self,
        *,
        guild_id: int,
        user_id: int,
        source_interaction: discord.Interaction,
        bot,
    ):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.user_id = user_id
        self.source_interaction = source_interaction

        from bot import Bot

        self.bot: Bot = bot

        self.init_components()

    def init_components(self) -> None:
        # Get guild icon pfp
        guild_icon = self.bot.get_guild(self.guild_id).icon

        # Main text section
        self.section = discord.ui.Section(
            discord.ui.TextDisplay(
                "\n".join(
                    [
                        "## Select Setting",
                        "Select the setting category using the buttons below.",
                    ]
                )
            ),
            accessory=discord.ui.Thumbnail(
                media=guild_icon.url if guild_icon is not None else R6URL.ICON
            ),
        )

        # Add select buttons ActionRow
        self.button_row = SettingsSelectButtons(view=self)

        # Group everything in a container
        container = discord.ui.Container(
            self.section, self.button_row, accent_color=discord.Color.blurple()
        )

        self.add_item(container)
