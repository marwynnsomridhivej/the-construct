__all__ = (
    "PlayerAlreadyExists",
    "PlayerDoesNotExist",
)


class PlayerAlreadyExists(Exception):
    """Exception raised when attempting to create a new StatsPlayer
    instance when one already exists with the same user ID.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id

    def __str__(self) -> str:
        return f"PlayerAlreadyExist[user_id={self.user_id}]"


class PlayerDoesNotExist(Exception):
    """Exception raised when attempting to reference a StatsPlayer
    instance that does not exist.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id

    def __str__(self) -> str:
        return f"PlayerDoesNotExist[user_id={self.user_id}]"
