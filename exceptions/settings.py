__all__ = (
    "InvalidMapPoolName",
    "MapPoolAlreadyExists",
    "MapPoolNotFound",
)


class InvalidMapPoolName(ValueError):
    """Exception raised when attempting to set a map pool's name
    to an invalid string of text.
    """

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"InvalidMapPoolName[name={self.name}]"


class MapPoolAlreadyExists(ValueError):
    """Exception raised when attempting to create a map pool
    when one already exists with the same name.
    """

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"MapPoolAlreadyExists[name={self.name}]"


class MapPoolNotFound(ValueError):
    """Exception raised when attempting to perform a map pool
    operation on a map pool that does not exist.
    """

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return f"MapPoolNotFound[name={self.name}]"
