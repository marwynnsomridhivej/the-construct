__all__ = ("InvalidGuildID",)


class InvalidGuildID(KeyError):
    """Exception raise when given an invalid guild ID."""

    def __init__(self, guild_id: int):
        self.guild_id = guild_id

    def __str__(self):
        return f"InvalidGuildID[guild_id={self.guild_id}]"
