__all__ = (
    "ICON",
    "ephemeral",
)


# Constants
ICON = "https://img.icons8.com/ios_filled/1200/rainbow-six-siege.jpg"


# Util functions
def ephemeral(*, seconds: int = 5) -> dict:
    return {
        "ephemeral": True,
        "delete_after": seconds,
    }
