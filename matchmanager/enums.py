from enum import StrEnum
from typing import List

__all__ = (
    "R6Map",
    "R6Side",

    "R6_RANKED",
    "R6_QUICKMATCH",
)


class R6Map(StrEnum):
    # fmt: off
    CASINO: str     = "calypso_casino"
    BORDER: str     = "border"
    DISTRICT: str   = "district"
    BANK: str       = "bank"
    KAFE: str       = "kafe_dostoyevsky"
    CHALET: str     = "chalet"
    CLUBHOUSE: str  = "clubhouse"
    STADIUM: str    = "stadium_2020"
    BRAVO: str      = "stadium_bravo"
    LAIR: str       = "lair"
    NIGHTHAVEN: str = "nighthaven_labs"
    CQ: str         = "close_quarter"
    EMERALD: str    = "emerald_plains"
    COASTLINE: str  = "coastline"
    CONSULATE: str  = "consulate"
    FAVELA: str     = "favela"
    FORTRESS: str   = "fortress"
    HEREFORD: str   = "hereford_base"
    HOUSE: str      = "house"
    KANAL: str      = "kanal"
    OREGON: str     = "oregon"
    OUTBACK: str    = "outback"
    PLANE: str      = "presidential_plane"
    SKYSCRAPER: str = "skyscraper"
    THEMEPARK: str  = "theme_park"
    TOWER: str      = "tower"
    VILLA: str      = "villa"
    YACHT: str      = "yacht"
    # fmt: on


class R6Side(StrEnum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


R6_RANKED: List[R6Map] = sorted([
    R6Map.CASINO,
    R6Map.CHALET,
    R6Map.BANK,
    R6Map.BORDER,
    R6Map.CLUBHOUSE,
    R6Map.KAFE,
    R6Map.LAIR,
    R6Map.NIGHTHAVEN,
    R6Map.COASTLINE,
    R6Map.CONSULATE,
    R6Map.FORTRESS,
    R6Map.OREGON,
    R6Map.OUTBACK,
])

R6_QUICKMATCH: List[R6Map] = sorted([
    R6Map.CASINO,
    R6Map.HOUSE,
    R6Map.OREGON,
    R6Map.CLUBHOUSE,
    R6Map.PLANE,
    R6Map.CONSULATE,
    R6Map.BANK,
    R6Map.KANAL,
    R6Map.CHALET,
    R6Map.KAFE,
    R6Map.YACHT,
    R6Map.BORDER,
    R6Map.FAVELA,
    R6Map.SKYSCRAPER,
    R6Map.COASTLINE,
    R6Map.THEMEPARK,
    R6Map.TOWER,
    R6Map.VILLA,
    R6Map.FORTRESS,
    R6Map.OUTBACK,
    R6Map.EMERALD,
    R6Map.BRAVO,
    R6Map.NIGHTHAVEN,
    R6Map.LAIR,
    R6Map.STADIUM,
])


# Sanity checks
for category in [R6_RANKED, R6_QUICKMATCH]:
    for _map in category:
        assert category.count(_map) == 1
