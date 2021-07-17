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

import discord


UNKNOWN_INTERACTION = 10062


class View(discord.ui.View):
    async def on_error(self, error, item, interaction):
        # This might seem like a bad idea, however even interactions
        # That Mousey immediately defers sometimes raise a not found error
        # Which in the end is just useless noise when trying to find bugs.
        if not isinstance(error, discord.NotFound) or error.code != UNKNOWN_INTERACTION:
            await super().on_error(error, item, interaction)
