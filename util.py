__all__ = ("ephemeral",)


def ephemeral(*, seconds: int = 5) -> dict:
    return {
        "ephemeral": True,
        "delete_after": seconds,
    }
