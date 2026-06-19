__all__ = (
    "AdminNotFound",
    "InvalidMapPoolName",
    "MapPoolAlreadyExists",
    "MapPoolNotFound",
    "MapPoolNotOwner",
)


class AdminNotFound(KeyError):
    def __init__(self, user_id: int):
        self.user_id = user_id

    def __str__(self):
        return f"AdminNotFound[user_id={self.user_id}]"


class InvalidMapPoolName(ValueError):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"InvalidMapPoolName[name={self.name}]"


class MapPoolAlreadyExists(ValueError):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"MapPoolAlreadyExists[name={self.name}]"


class MapPoolNotFound(ValueError):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"MapPoolNotFound[name={self.name}]"


class MapPoolNotOwner(ValueError):
    def __init__(self, owner_id: int, user_id: int):
        self.owner_id = owner_id
        self.user_id = user_id

    def __str__(self):
        return f"MapPoolNotOwner[owner_id={self.owner_id}, user_id={self.user_id}]"
