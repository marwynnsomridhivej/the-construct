import discord

from event import PrematchDMPayload
from util import ICON

__all__ = ("MatchStartDMView",)


class MatchStartDMView(discord.ui.LayoutView):
    def __init__(self, *, guild: discord.Guild, payload: PrematchDMPayload):
        super().__init__(timeout=None)

        self._guild = guild
        self._payload = payload
        self._entry = payload.queue_entry

        self.init_components()

    @property
    def text_display(self) -> list[discord.ui.Item]:
        items = []

        # Instructions
        pregame_instr = discord.ui.TextDisplay(
            "\n".join(
                [
                    "### Pre-Game Instructions",
                    f"1. Join the voice channel <#{self._payload.voice_channel_id}>",
                    "1. Team captains will draft players one by one",
                    "  - -# If player count is EVEN, the lower rated captain will get to pick first, "
                    + "and picks alternate until no players remain",
                    "  - -# If player count is ODD, the higher rated captain will get to pick first, "
                    + "and picks alternate until one player remains. The last player will be drafted  "
                    + "into the team of the lower rated captain automatically",
                    "  - -# If the match was started with auto draft enabled, players will be automatically "
                    + "distributed to create the most balanced teams possible",
                    "1. Teams are split into isolated voice channels based on player draft",
                    "  - -# Players are automatically moved by the bot and will only be able to see "
                    + "their own team's voice channel. Captains and the queue owner can travel "
                    + "between both voice channels for administrative purposes only",
                    "1. Team captains will alternate map bans until three maps remain",
                    "  - -# The higher rated captain will get to ban first",
                    "1. The bot will randomly select a map from the three remaining maps "
                    + "as the map this match is to be played on",
                    "1. The higher rated captain will select what side their team will start first"
                    "1. The queue owner will create a custom lobby and invite all players"
                    "  - -# Players will arrange themselves according to the draft",
                ]
            )
        )
        items.append(pregame_instr)
        items.append(discord.ui.Separator())

        postgame_instr = discord.ui.TextDisplay(
            "\n".join(
                [
                    "### Post-Game Instructions",
                    "1. Team captains will designate one member from their team as the MVP",
                    "1. The queue owner will report the match results",
                    "1. After MVP designations and results are finalised, player rankings will "
                    + "be automatically adjusted based on match outcome",
                ]
            )
        )
        items.append(postgame_instr)
        items.append(discord.ui.Separator())

        # Match Details (mode, players, captains)
        details = discord.ui.TextDisplay(
            "\n".join(
                [
                    "### Details",
                    f"- Draft Panel Message: {self._payload.message.jump_url}",
                    f"- Mode: `{self._entry.type}`",
                    f"- Players: `{len(self._entry.players)}/{self._entry.max_players}`",
                    "\n".join([f"  - <@{player}>" for player in self._entry.players]),
                    f"- Captains: {' and '.join([f'<@{capt_id}>' for capt_id in self._payload.captains])}",
                ]
            )
        )
        items.append(details)
        items.append(discord.ui.Separator())
        return items

    def init_components(self) -> None:
        container = discord.ui.Container(
            discord.ui.Section(
                # Header with basic title
                discord.ui.TextDisplay(f"## Match Starting in {self._guild.name}"),
                self.text_display[0],
                accessory=discord.ui.Thumbnail(
                    self._guild.icon.url if self._guild.icon is not None else ICON
                ),
            ),
            # Actual part that displays details and instructions
            *self.text_display[1:],
            # Separator is already padded at the end in *text_display
            discord.ui.TextDisplay(
                "-# This is an automated message sent to all players that queued for "
                + f"{self._payload.match_name} in the server {self._guild.name}. "
                + "If you received this message in error, please notify your server admin."
            ),
            # Accent color
            accent_color=discord.Color.blurple(),
        )
        self.add_item(container)
