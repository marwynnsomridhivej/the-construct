import discord

__all__ = (
    "InvalidCaptainManualSelect",
    "InvalidUserSelected",
    "UserIsBot",
)


class InvalidCaptainManualSelect(Exception):
    pass


class InvalidUserSelected(Exception):
    def __init__(self, user: discord.User):
        self.user = user

    def __str__(self):
        return f"InvalidUserSelected[user={self.user.id}]"


class UserIsBot(Exception):
    def __init__(self, user: discord.User):
        self.user = user

    def __str__(self):
        return f"UserIsBot[user={self.user.id}]"
