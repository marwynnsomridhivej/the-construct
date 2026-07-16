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
    """Exception raised when attempting to reference a match that
    already exists.
    """

    def __init__(self, match_name: str):
        self.match_name = match_name
        self.msg = f'Match with name "{match_name}" already exists'

    def __str__(self):
        return f"MatchAlreadyExists[name={self.match_name}]"


class MatchDoesNotExist(Exception):
    """Exception raised when attempting to reference a match that
    doesn't exist.
    """

    def __init__(self, match_name: str):
        self.match_name = match_name

    def __str__(self):
        return f"MatchDoesNotExist[queue_name={self.match_name}]"


class MatchFinalised(Exception):
    """Exception raised when attempting to reference a match that
    has already been finalised.
    """

    pass


class CaptainAlreadyAssigned(Exception):
    """Exception raised when attempting to assign a team captain
    to a team that already has one assigned to it.
    """

    pass


class CaptainNotAssigned(Exception):
    """Exception raised when attempting to perform any team operations
    prior to assigning a team captain.
    """

    pass


class MapAlreadyBanned(Exception):
    """Exception raised when attempting to ban a map that has already
    been banned.
    """

    pass


class MVPAlreadyAssigned(Exception):
    """Exception raised when attempting to designate a team's MVP
    when one has already been assigned.
    """

    pass


class RoundsWonTeamWonMismatch(ValueError):
    """Exception raised when the amount of rounds won by each team does not
    reflect the team that was reported to win the match.
    """

    pass
