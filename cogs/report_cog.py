import discord
from discord import app_commands
from discord.ext import commands

from canned import Canned
from ui import FeedbackModal


class ReportsCog(commands.Cog):
    def __init__(self, bot):
        from bot import Bot

        self.bot: Bot = bot

    async def cog_load(self):
        self.bot.logger.info("[ReportsCog] Successfully loaded")

    @app_commands.command(
        name="feedback", description="Send feedback to the bot developer"
    )
    @app_commands.checks.cooldown(1.0, 300.0)
    @app_commands.guild_only()
    async def _report_command(self, interaction: discord.Interaction):
        feedback_modal = FeedbackModal(bot=self.bot)
        await interaction.response.send_modal(feedback_modal)

    @_report_command.error
    async def on_feedback_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                Canned.ERR_COOLDOWN.format(int(error.cooldown.get_retry_after())),
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(ReportsCog(bot))
