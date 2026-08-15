__all__ = ("InvalidGuildID", "MatchPanelStateException")


class InvalidGuildID(KeyError):
    """Exception raise when given an invalid guild ID."""

    def __init__(self, guild_id: int):
        self.guild_id = guild_id

    def __str__(self):
        return f"InvalidGuildID[guild_id={self.guild_id}]"


class MatchPanelStateException(Exception):
    """Exception raised when an operation is performed after the match
    panel state has been changed.
    """
