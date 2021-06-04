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
from discord.ext import commands


def has_any_permission(**permissions):
    invalid = [x for x in permissions if x not in discord.Permissions.VALID_FLAGS]

    if invalid:
        raise TypeError(f'Invalid permissions specified: {invalid}')

    def predicate(ctx):
        perms = ctx.channel.permissions_for(ctx.author)

        if perms.administrator:
            return True

        found = [x for x in permissions if getattr(perms, x)]

        if found:
            return True

        raise commands.MissingPermissions(found)

    return commands.check(predicate)
