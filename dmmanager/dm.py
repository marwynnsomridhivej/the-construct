from base import WrapperBase


class DMWrapper(WrapperBase):
    """Wrapper class that wraps DM related data from the database into
    a python object.
    """

    __slots__ = ("data",)

    def __init__(self, data: dict[str, int]):
        self.data = data

    @staticmethod
    def _key(guild_id: int, user_id: int) -> str:
        """Create a dictionary key based on guild and user IDs.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The user ID of the player.

        Returns:
            str: The key to be used inside the dictionary for the
                guild ID and user ID combination.
        """
        return f"{guild_id}_{user_id}"

    def get(self, guild_id: int, user_id: int) -> int | None:
        """Get a message ID for the specified guild ID and user ID
        combination.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The user ID of the player.

        Returns:
            int | None: The corresponding message ID, if one exists.
        """
        return self.data.get(self._key(guild_id, user_id))

    def create(self, guild_id: int, user_id: int, message_id: int) -> None:
        """Create an entry to be stored for the specified guild ID, user
        ID, and message ID.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The user ID of the player.
            message_id (int): The ID of the message.
        """
        self.data[self._key(guild_id, user_id)] = message_id

    def delete(self, guild_id: int, user_id: int) -> int:
        """Delete an entry from the database for the specified guild ID
        and user ID.

        Args:
            guild_id (int): The ID of the guild.
            user_id (int): The user ID of the player.

        Returns:
            int: The message ID of the corresponding entry.
        """
        return self.data.pop(self._key(guild_id, user_id))

    def serialise(self) -> dict:
        """Convert the wrapper class into a JSON serialisable object.

        Returns:
            dict: A JSON serialisable representation of this wrapper.
        """
        return self.data
