# -*- coding: utf-8 -*-

"""
Mousey: Discord Moderation Bot
Copyright (C) 2016 - 2021 Lilly Rose Berner

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import asyncio
import inspect

import discord

from ... import ExitableMenu, disable_when_pressed
from ...utils import join_parts


def match_prefix(argument):
    return len(argument) <= 25 and '\n' not in argument


class PrefixMenu(ExitableMenu):
    async def get_content(self):
        config = self.mousey.get_cog('Config')
        prefixes = await config.get_prefixes(self.guild)

        if not prefixes:
            active = 'No custom prefixes configured.'
        else:
            active = f'Active custom prefixes:{join_parts(prefixes)}'

        content = inspect.cleandoc(
            """
            **__Custom Prefix Configuration__**

            {active}

            You can add up to 10 custom prefixes.
            """
        )

        return content.format(active=active)

    async def update_components(self):
        config = self.mousey.get_cog('Config')
        prefixes = await config.get_prefixes(self.guild)

        if not prefixes:
            self.add_prefix.disabled = False
            self.remove_prefix.disabled = True
        elif len(prefixes) >= 10:
            self.add_prefix.disabled = True
            self.remove_prefix.disabled = False
        else:
            self.add_prefix.disabled = False
            self.remove_prefix.disabled = False

    @discord.ui.button(label='Add Prefix', style=discord.ButtonStyle.primary)
    @disable_when_pressed
    async def add_prefix(self, interaction, button):
        config = self.mousey.get_cog('Config')
        prefixes = await config.get_prefixes(self.guild)

        try:
            prefix = await self.prompt(
                'Send the prefix you would like to add!',
                check=match_prefix,
                interaction=interaction,
            )
        except asyncio.TimeoutError:
            return

        prefixes.append(prefix)
        await config.set_prefixes(self.guild, prefixes)

    @discord.ui.button(label='Remove Prefix', style=discord.ButtonStyle.danger)
    @disable_when_pressed
    async def remove_prefix(self, interaction, button):
        config = self.mousey.get_cog('Config')
        prefixes = await config.get_prefixes(self.guild)

        try:
            prefix = await self.pick('Select a prefix to remove.', interaction=interaction, options=prefixes)
        except asyncio.TimeoutError:
            return

        prefixes.remove(prefix)
        await config.set_prefixes(self.guild, prefixes)
