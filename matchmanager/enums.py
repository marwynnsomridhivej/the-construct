from enum import StrEnum

__all__ = (
    "R6Map",
    "R6Side",
    "R6_RANKED",
    "R6_QUICKMATCH",
    "R6_MAX_PLAYERS_PER_TEAM",
)


class R6Map(StrEnum):
    # fmt: off
    CASINO =        "calypso_casino"
    BORDER =        "border"
    DISTRICT =      "district"
    BANK =          "bank"
    KAFE =          "kafe_dostoyevsky"
    CHALET =        "chalet"
    CLUBHOUSE =     "clubhouse"
    STADIUM =       "stadium_2020"
    BRAVO =         "stadium_bravo"
    LAIR =          "lair"
    NIGHTHAVEN =    "nighthaven_labs"
    CQ =            "close_quarter"
    EMERALD =       "emerald_plains"
    COASTLINE =     "coastline"
    CONSULATE =     "consulate"
    FAVELA =        "favela"
    FORTRESS =      "fortress"
    HEREFORD =      "hereford_base"
    HOUSE =         "house"
    KANAL =         "kanal"
    OREGON =        "oregon"
    OUTBACK =       "outback"
    PLANE =         "presidential_plane"
    SKYSCRAPER =    "skyscraper"
    THEMEPARK =     "theme_park"
    TOWER =         "tower"
    VILLA =         "villa"
    YACHT =         "yacht"
    # fmt: on


class R6Side(StrEnum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


R6_RANKED: list[R6Map] = sorted(
    [
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
    ]
)

R6_QUICKMATCH: list[R6Map] = sorted(
    [
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
    ]
)

R6_MAX_PLAYERS_PER_TEAM: int = 5


# Sanity checks
for category in [R6_RANKED, R6_QUICKMATCH]:
    for _map in category:
        assert category.count(_map) == 1
