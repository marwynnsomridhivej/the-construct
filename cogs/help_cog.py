import discord
from discord import app_commands
from discord.ext import commands

HELP_URL = (
    "https://github.com/marwynnsomridhivej/nexus/blob/main/README.md#getting-started"
)


class HelpCog(commands.Cog):
    def __init__(self, bot):
        from bot import Bot

        self.bot: Bot = bot

    async def cog_load(self):
        self.bot.logger.info("[HelpCog] Successfully loaded")

    @app_commands.command(name="help", description="Displays command information")
    async def _help_command(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Detailed command usage can be found [here]({HELP_URL})",
            ephemeral=True,
            suppress_embeds=True,
        )


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
