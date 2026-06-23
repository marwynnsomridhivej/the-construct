import logging
import logging.handlers
import subprocess
import sys
from datetime import datetime

import discord
from discord.ext import commands

from config import Config
from dmmanager import DMManager
from matchmanager import MatchManager
from queuemanager import QueueManager
from settingsmanager import SettingsManager
from statsmanager import StatsManager


class Bot(commands.Bot):
    __version__ = "2.1.0-beta"
    __commit__ = (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )

    def __init__(self, config: Config, **kwargs):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.command_prefix),
            activity=discord.Activity(
                name=f"v{self.__version__} | {self.__commit__}",
                type=discord.ActivityType.playing,
            ),
            owner_ids=config.owner_ids,
            **kwargs,
        )

        # Configuration from config.json
        self.config = config

        # Get and store root logger
        self.logger = logging.getLogger()

        # Managers for IO
        self.dm_manager: DMManager = DMManager(self.config.data_dir, self)
        self.match_manager: MatchManager = MatchManager(self.config.data_dir)
        self.queue_manager: QueueManager = QueueManager(self.config.data_dir)
        self.stats_manager: StatsManager = StatsManager(self.config.data_dir)
        self.settings_manager: SettingsManager = SettingsManager(self.config.data_dir)

        # Should we wipe DMs with everyone?
        self.dm_wipe = kwargs.get("dm_wipe")

        # Is prod?
        self.prod = kwargs.get("prod")

    async def setup_hook(self):
        # Initialise managers
        await self.dm_manager.load()
        await self.match_manager.load()
        await self.queue_manager.load()
        await self.stats_manager.load()
        await self.settings_manager.load()

        # Load all cogs
        for cog in self.config.cogs:
            try:
                await self.load_extension(cog)
            except Exception as e:
                self.logger.error(f"Could not load cog {cog}: {e}")
                raise e

        # Sync slash commands
        if not self.prod:
            guild = discord.Object(id=self.config.nexus_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

        self.logger.info(
            f"[BOT] v{self.__version__} ({self.__commit__}) successfully loaded"
        )

    async def on_ready(self):
        await self.wait_until_ready()
        await self.dm_manager.purge_all()
        for guild in self.guilds:
            await self.settings_manager.create_guild_settings(guild.id, new_only=True)

        if not self.dm_wipe:
            return

        # Delete any stragglers
        for user in self.users:
            # Don't do bots
            if user.bot:
                continue

            deleted_ids = []
            dm_channel = await user.create_dm()
            async for message in dm_channel.history(limit=None):
                # Don't delete messages we aren't the author of
                if message.author.id != self.user.id:
                    continue

                await message.delete()
                deleted_ids.append(message.id)
                self.logger.info(
                    f"Deleted message ID {message.id} for user {user.display_name} ({user.id}) in DMs"
                )

            if not deleted_ids:
                self.logger.info(
                    f"Did not find any deletable DMs with user {user.display_name} ({user.id})"
                )


if __name__ == "__main__":
    # Set flags
    debug = len(sys.argv) > 1 and "debug" in sys.argv
    dm_wipe = len(sys.argv) > 1 and "wipe" in sys.argv
    prod = len(sys.argv) > 1 and "prod" in sys.argv

    # Load bot config from disk
    config = Config()

    # Create root logger and set logging level
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Create rotating file and stream handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=f"{config.log_dir}/{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.log",
        maxBytes=16 * 1024 * 1024,  # 16 MiB
        backupCount=10,
        encoding="utf-8",
    )
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)

    # Set formatter and add handler to root logger
    for handler in [file_handler, stdout_handler]:
        # For type hint
        assert isinstance(handler, logging.Handler)
        handler.setFormatter(
            logging.Formatter(
                "[{asctime}] [{levelname}] {name}: {message}",
                r"%Y-%m-%d %H:%M:%S",
                style="{",
            )
        )
        logger.addHandler(handler)

    # Run bot
    bot = Bot(config, intents=discord.Intents.all(), dm_wipe=dm_wipe, prod=prod)
    bot.run(config.token, log_handler=None)
