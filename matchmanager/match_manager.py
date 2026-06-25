from datetime import datetime

from base import ManagerBase
from event import AutoDraftPayload, MatchPayload

from .enums import R6Map, R6Side
from .match import MatchEntry, MatchTeam, MatchWrapper


class MatchManager(ManagerBase):
    def __init__(self, match_loc: str):
        super().__init__(match_loc, "matches")

    async def load(self):
        await super().load(name="MatchManager")

    async def _get_or_create_wrapper(self) -> MatchWrapper:
        return await super()._get_or_create_wrapper(cls=MatchWrapper)

    def _get_starting_side(
        self, team: MatchTeam, captain_id: int, choice: R6Side
    ) -> R6Side:
        flip = {
            R6Side.ATTACKER: R6Side.DEFENDER,
            R6Side.DEFENDER: R6Side.ATTACKER,
        }
        return choice if team.captain_id == captain_id else flip[choice]

    async def create_match(
        self, *, payload: MatchPayload, auto_draft: AutoDraftPayload = None
    ) -> None:
        wrapper = await self._get_or_create_wrapper()

        # Init two empty teams
        team_a = MatchTeam.create_empty("A")
        team_b = MatchTeam.create_empty("B")

        if payload.auto_draft and auto_draft is not None:
            # Assign captains to each team from auto draft payload
            team_a.assign_captain(auto_draft.team_a_captain)
            team_b.assign_captain(auto_draft.team_b_captain)
            payload.set_auto_draft_captains(auto_draft)

            # Draft players to each team
            for team, players in [
                (team_a, auto_draft.team_a_players),
                (team_b, auto_draft.team_b_players),
            ]:
                for player_id in players:
                    team.draft_player(player_id)
        else:
            # Assign captains from payload
            team_a.assign_captain(payload.captains[0])
            team_b.assign_captain(payload.captains[1])

        # Craft entry data
        match_entry_data = {
            "created_timestamp": int(datetime.now().timestamp()),
            "type": payload.queue_entry.type,
            "voice_channel_id": payload.voice_channel_id,
            "team_a": team_a.serialise(),
            "team_b": team_b.serialise(),
            "map": None,
        }

        # Create match entry
        wrapper.get_or_create(payload.guild_id).create(
            payload.match_name,
            match_entry_data,
        )

        # Write to disk
        await self.write(wrapper)

    async def delete_match(self, guild_id: int, name: str) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get_or_create(guild_id).delete(name)
        await self.write(wrapper)

    async def get_match(self, guild_id: int, name: str) -> MatchEntry:
        wrapper = await self._get_or_create_wrapper()
        return wrapper.get(guild_id, throw=True).get(name, throw=True)

    async def has_running_match(self, guild_id: int) -> bool:
        wrapper = await self._get_or_create_wrapper()
        return bool(wrapper.get(guild_id, throw=True).data)

    async def draft_player(
        self, guild_id: int, name: str, captain_id: int, player_id: int
    ) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).get_team_of_user(
            captain_id
        ).draft_player(player_id)
        await self.write(wrapper)

    async def ban_map(
        self, guild_id: int, name: str, captain_id: int, choice: R6Map
    ) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).ban_map(
            captain_id, choice
        )
        await self.write(wrapper)

    async def select_map(self, guild_id: int, name: str, choice: R6Map) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).set_map(choice)
        await self.write(wrapper)

    async def select_starting_side(
        self, guild_id: int, name: str, captain_id: int, choice: R6Side
    ) -> None:
        wrapper = await self._get_or_create_wrapper()
        mgc = wrapper.get(guild_id, throw=True).get(name, throw=True)
        mgc.team_a.starting_side = self._get_starting_side(
            mgc.team_a, captain_id, choice
        )
        mgc.team_b.starting_side = self._get_starting_side(
            mgc.team_b, captain_id, choice
        )
        await self.write(wrapper)

    async def designate_mvp(self, guild_id: int, name: str, mvp_id: int) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).designate_mvp(mvp_id)
        await self.write(wrapper)

    async def set_winning_team(self, guild_id: int, name: str, captain_id: int) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).designate_winner(
            captain_id
        )
        await self.write(wrapper)

    async def set_team_rounds_won(
        self, guild_id: int, name: str, captain_id: int, rounds_won: int
    ) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).set_rounds_won(
            captain_id, rounds_won
        )
        await self.write(wrapper)

    async def set_team_vc(
        self, guild_id: int, name: str, captain_id: int, vc_id: int
    ) -> None:
        wrapper = await self._get_or_create_wrapper()
        wrapper.get(guild_id, throw=True).get(name, throw=True).get_team_of_user(
            captain_id
        ).voice_channel_id = vc_id
        await self.write(wrapper)

    async def reset_draft(self, guild_id: int, payload: MatchPayload) -> None:
        wrapper = await self._get_or_create_wrapper()
        entry = wrapper.get(guild_id, throw=True).get(payload.match_name, throw=True)
        entry.reset_draft(auto_draft=payload.auto_draft)
        entry.map = None
        await self.write(wrapper)
