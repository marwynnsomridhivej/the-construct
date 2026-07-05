import discord

from util import titlecase

from ..feedback_type import FeedbackType

__all__ = ("FeedbackView",)


class FeedbackView(discord.ui.LayoutView):
    def __init__(
        self,
        *,
        feedback_type: FeedbackType,
        content: str,
        interaction: discord.Interaction,
    ):
        super().__init__()
        self.feedback_type = feedback_type
        self.content = content
        self.interaction = interaction

        self.init_components()

    def init_components(self) -> None:
        guild = self.interaction.guild
        assert guild is not None

        container = discord.ui.Container(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    f"## Feedback Submission - {titlecase(self.feedback_type)}"
                ),
                discord.ui.TextDisplay(
                    "\n".join(
                        [
                            "### User Information",
                            f"- User: {self.interaction.user.mention} | `{self.interaction.user.id}`",
                            f"- Guild: `{guild.name}` | `{guild.id}`",
                            f"- Sent at: <t:{int(self.interaction.created_at.timestamp())}:f>",
                        ]
                    ),
                ),
                accessory=discord.ui.Thumbnail(
                    self.interaction.user.avatar.url
                    if self.interaction.user.avatar is not None
                    else self.interaction.user.default_avatar.url
                ),
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay(f"### Content\n{self.content}"),
            # Accent color
            accent_color=discord.Color.blurple(),
        )
        self.add_item(container)
