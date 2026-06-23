import traceback

import discord

from canned import Canned

from ..feedback_type import FEEDBACK_TYPES, FeedbackType

__all__ = ("FeedbackModal",)


class FeedbackModal(discord.ui.Modal):
    def __init__(self, *, bot):
        super().__init__(title="Feedback Submission Form")

        from bot import Bot

        self.bot: Bot = bot

        self.init_components()

    def init_components(self) -> None:
        self.feedback_type = discord.ui.Label(
            text="Feedback Type",
            description="Please designate the type of feedback you are giving",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(label=opt.title(), value=opt)
                    for opt in FEEDBACK_TYPES
                ]
            ),
        )

        self.feedback_content = discord.ui.Label(
            text="Content",
            description="Please enter your feedback here (up to 3000 characters)",
            component=discord.ui.TextInput(
                style=discord.TextStyle.paragraph,
                placeholder="Enter feedback here",
                min_length=1,
                max_length=3000,
            ),
        )

        for item in [self.feedback_type, self.feedback_content]:
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        # Type hints
        assert isinstance(self.feedback_type.component, discord.ui.RadioGroup)
        assert isinstance(self.feedback_content.component, discord.ui.TextInput)

        from ..views import FeedbackView

        feedback_view = FeedbackView(
            feedback_type=FeedbackType(self.feedback_type.component.value),
            content=self.feedback_content.component.value,
            interaction=interaction,
        )

        # Send to all owners as a silent message
        for owner_id in self.bot.config.owner_ids:
            await self.bot.get_user(owner_id).send(
                view=feedback_view,
                silent=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )

        await interaction.response.send_message(Canned.FEEDBACK_CONF, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        self.bot.logger.error(
            f"An exception occurred when trying to send feedback: {error}"
        )
        traceback.print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(f"An error has occurred: {error}")
