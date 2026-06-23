__all__ = (
    "MatchAlreadyExists",
    "MatchDoesNotExist",
    "MatchFinalised",
    "CaptainAlreadyAssigned",
    "CaptainNotAssigned",
    "MapAlreadyBanned",
    "MVPAlreadyAssigned",
    "RoundsWonTeamWonMismatch",
)


class MatchAlreadyExists(Exception):
    def __init__(self, match_name: str):
        self.match_name = match_name
        self.msg = f'Match with name "{match_name}" already exists'

    def __str__(self):
        return f"MatchAlreadyExists[name={self.match_name}]"


class MatchDoesNotExist(Exception):
    def __init__(self, match_name: str):
        self.match_name = match_name

    def __str__(self):
        return f"MatchDoesNotExist[queue_name={self.match_name}]"


class MatchFinalised(Exception):
    pass


class CaptainAlreadyAssigned(Exception):
    pass


class CaptainNotAssigned(Exception):
    pass


class MapAlreadyBanned(Exception):
    pass


class MVPAlreadyAssigned(Exception):
    pass


class RoundsWonTeamWonMismatch(ValueError):
    pass
