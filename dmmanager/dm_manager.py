import discord

from base import ManagerBase

from .dm import DMWrapper


class DMManager(ManagerBase):
    def __init__(self, dm_loc: str, bot):
        super().__init__(dm_loc, "dms")

        from bot import Bot

        self.bot: Bot = bot

    async def load(self):
        await super().load(name="DMManager")

    async def _get_or_create_wrapper(self) -> DMWrapper:
        return await super()._get_or_create_wrapper(cls=DMWrapper)

    async def purge_all(self) -> None:
        wrapper = await self._get_or_create_wrapper()
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
        wrapper = await self._get_or_create_wrapper()
        if wrapper.get(guild_id, user_id) is not None:
            raise KeyError(
                f"Entry already exists for guild_id {guild_id} and user_id {user_id}"
            )
        wrapper.create(guild_id, user_id, message_id)
        await self.write(wrapper)

    async def delete(self, guild_id: int, user_id: int) -> int:
        wrapper = await self._get_or_create_wrapper()
        message_id = wrapper.delete(guild_id, user_id)
        await self.write(wrapper)
        return message_id
