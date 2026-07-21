from enum import StrEnum

__all__ = (
    "SettingsChoice",
    "MapPoolName",
    "ALL_SETTINGS_CHOICES",
    "DEFAULT_MAP_POOL_NAMES",
    "PER_GUILD_MAP_POOL_LIMIT",
    "PER_MAP_POOL_LIMIT",
)


class SettingsChoice(StrEnum):
    """Standard text representation of settings command choices."""

    GENERAL = "general"
    MAP_POOL = "map pool"


class MapPoolName(StrEnum):
    """Standard text representation of default map pool names."""

    RANKED = "default - ranked"
    QUICKMATCH = "default - quickmatch"


# Consts for util
ALL_SETTINGS_CHOICES = [
    SettingsChoice.GENERAL,
    SettingsChoice.MAP_POOL,
]
"""All settings choices."""


DEFAULT_MAP_POOL_NAMES = [
    MapPoolName.RANKED,
    MapPoolName.QUICKMATCH,
]
"""All default map pool names."""


PER_GUILD_MAP_POOL_LIMIT = 10
"""The maximum number of custom map pools a guild can have."""


PER_MAP_POOL_LIMIT = 20
"""The maximum number of maps a custom map pool can contain."""
