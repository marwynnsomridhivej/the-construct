from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from base import ManagerBase

from .dm import DMWrapper

if TYPE_CHECKING:
    from bot import Bot


class DMManager(ManagerBase):
    """Database manager to keep track of and delete DMs when necessary."""

    def __init__(self, dm_loc: str, bot):
        super().__init__(dm_loc, "dms")
        self.bot: Bot = bot

    async def load(self):
        """Create the necessary directories and load into memory."""
        await super()._load(name="DMManager")

    async def get_or_create_wrapper(self) -> DMWrapper:
        """Get or create the DMWrapper.

        Returns:
            DMWrapper: The existing or newly created DMWrapper.
        """
        return await super()._get_or_create_wrapper(cls=DMWrapper)

    async def purge_all(self) -> None:
        """Purge all tracked DMs."""
        wrapper = await self.get_or_create_wrapper()
        for identifier, message_id in wrapper.data.items():
            user_id = [int(_id) for _id in identifier.split("_")][1]
            user = self.bot.get_user(user_id)
            if user is None:
                continue
            dm_channel = await user.create_dm()
            try:
                await dm_channel.get_partial_message(message_id).delete()
                self.bot.logger.info(
                    f"Deleted message ID {message_id} for user {user_id}"
                )
            except discord.NotFound:
                self.bot.logger.info(
                    f"Message ID {message_id} for user {user_id} was already deleted"
                )
            except discord.HTTPException as e:
                self.bot.logger.error(
                    f"HTTPException when trying to delete message ID {message_id} for user {user_id}: {e}"
                )
            except Exception as e:
                self.bot.logger.error(
                    "An exception occurred when trying to delete "
                    + f"message ID {message_id} for user {user_id}: {e}"
                )
        wrapper.data = {}
        await self.write(wrapper)

    async def create(self, guild_id: int, user_id: int, message_id: int) -> None:
        """Create an entry in the database corresponding to a DM that
        should be deleted in the future.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The user ID of the player.
            message_id (int): The ID of the message to be deleted.

        Raises:
            KeyError: An entry already exists.
        """
        wrapper = await self.get_or_create_wrapper()
        if wrapper.get(guild_id, user_id) is not None:
            raise KeyError(
                f"Entry already exists for guild_id {guild_id} and user_id {user_id}"
            )
        wrapper.create(guild_id, user_id, message_id)
        await self.write(wrapper)

    async def delete(self, guild_id: int, user_id: int) -> int:
        """Delete an entry from the database (not the actual message).

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The user ID of the player.

        Returns:
            int: The saved message ID.
        """
        wrapper = await self.get_or_create_wrapper()
        message_id = wrapper.delete(guild_id, user_id)
        await self.write(wrapper)
        return message_id
