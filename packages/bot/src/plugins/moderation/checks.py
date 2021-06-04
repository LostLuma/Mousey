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

from discord.ext import commands

from ... import VisibleCommandError


def guild_has_mute_role():
    async def predicate(ctx):
        moderation = ctx.bot.get_cog('Moderation')
        role = await moderation.get_mute_role(ctx.guild)

        if role is not None:
            return True

        raise VisibleCommandError('A mute role is required in order to execute this command.')

    return commands.check(predicate)
