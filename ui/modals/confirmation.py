import discord

from util import titlecase

__all__ = ("ConfirmationModal",)


class ConfirmationModal(discord.ui.Modal):
    def __init__(self, *, operation: str, custom: dict[str, str] = {}):
        super().__init__(title=f"{titlecase(operation)} Confirmation")

        # Allow for custom UI text
        self.custom_text = custom.get("text")
        self.custom_description = custom.get("description")
        self.custom_yes = custom.get("yes")
        self.custom_no = custom.get("no")

        self.init_components()
        self.proceed = False

    def init_components(self) -> None:
        self.confirm = discord.ui.Label(
            text=self.custom_text or "Are you sure?",
            description=self.custom_description
            or "This operation cannot be undone. "
            + "Only proceed if you know what you are doing.",
            component=discord.ui.RadioGroup(
                options=[
                    discord.RadioGroupOption(
                        label=self.custom_yes or "I understand and wish to proceed",
                        value="1",
                    ),
                    discord.RadioGroupOption(
                        label=self.custom_no or "No, take me back", value="0"
                    ),
                ]
            ),
        )
        self.add_item(self.confirm)

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.confirm.component, discord.ui.RadioGroup)
        assert self.confirm.component.value is not None

        self.proceed = int(self.confirm.component.value) == 1
        await interaction.response.defer()
