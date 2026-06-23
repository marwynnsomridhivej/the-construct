from typing import Union

import discord

from base import SettingsBaseView
from settingsmanager import PER_GUILD_MAP_POOL_LIMIT


class SettingsMapPoolView(SettingsBaseView):
    def __init__(
        self,
        *,
        guild_id: int,
        user_id: int,
        source_interaction: discord.Interaction,
        parent_view: discord.ui.LayoutView,
        bot,
    ):
        from .settings_buttons import SettingsMapPoolButtons

        super().__init__(
            guild_id=guild_id,
            user_id=user_id,
            source_interaction=source_interaction,
            button_cls=SettingsMapPoolButtons,
            parent_view=parent_view,
            bot=bot,
        )

    async def init_components(self):
        await super().init_components()

        # Check if user is server owner or bot admin
        if self.is_guild_owner or self.is_bot_admin:
            # Check if the server has custom map pools
            map_pools = await self.bot.settings_manager.get_all_map_pools(self.guild_id)
            pool_names = [pool.name for pool in map_pools]
            container = self.find_item(self.container_id)

            # If the server has custom map pools, show pool selector
            if pool_names:
                from .settings_buttons import SettingsMapPoolSelectRow

                self.map_pool_name_select = SettingsMapPoolSelectRow(
                    view=self,
                    names=pool_names,
                )

                assert isinstance(container, discord.ui.Container)
                container.add_item(self.map_pool_name_select)

            # Enable or disable edit and delete buttons based on existence of owned pols
            for item in self.main_buttons.children:
                assert isinstance(item, discord.ui.Button)
                if item.label in ["Edit", "Delete"]:
                    item.disabled = not bool(pool_names)

    async def get_text_content(self) -> str:
        items = []

        # View header
        header = "\n".join(
            [
                "## Map Pool Configuration",
                "Custom map pools can be created and used to customise what maps the bot will "
                + "curate for drafts. Any map pools created in this server will appear here. "
                + f"Each server can have up to `{PER_GUILD_MAP_POOL_LIMIT}` custom map pools.",
            ]
        )
        items.append(header)

        # Show map pool details
        map_pools = await self.bot.settings_manager.get_all_map_pools(self.guild_id)
        map_pool_details_text = "\n".join(
            [
                "\n".join(
                    [
                        f"### {pool.name.title()}",
                        f"> Owner: <@{pool.owner_id}>",
                        f"> Created: <t:{pool.created_timestamp}:f>",
                        f"> Modified: <t:{pool.modified_timestamp}:f>",
                        f"> Maps: `{len(pool)}`",
                    ]
                )
                for pool in map_pools
            ]
        )
        map_pools_text = "\n".join(
            [
                "## Custom Map Pools",
                map_pool_details_text
                if map_pool_details_text
                else "*No custom map pools have been created yet*",
            ]
        )
        items.append(map_pools_text)

        return "\n".join(items)

    def get_selected_map_pool_name(self) -> Union[str, None]:
        # If not admin, SettingsMapPoolView will not have the attribute map_pool_name_select
        if not hasattr(self, "map_pool_name_select"):
            return None

        if (value := self.map_pool_name_select.value) is not None:
            return value.lower()

        return None
