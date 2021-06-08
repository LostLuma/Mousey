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

from .errors import NoThreadChannels


def disable_in_threads():
    def predicate(ctx):
        # Always show commands in help
        if ctx.invoked_with == 'help':
            return True

        if not isinstance(ctx.channel, discord.Thread):
            return True

        raise NoThreadChannels()

    return commands.check(predicate)


def bot_has_permissions(**permissions):
    return _bot_has_permissions(True, **permissions)


def bot_has_guild_permissions(**permissions):
    return _bot_has_permissions(False, **permissions)


def _bot_has_permissions(local, **permissions):
    invalid = [x for x in permissions if x not in discord.Permissions.VALID_FLAGS]

    if invalid:
        raise TypeError(f'Invalid permissions specified: {invalid}')

    def predicate(ctx):
        # Always show commands in help
        if ctx.invoked_with == 'help':
            return True

        if not local:
            perms = ctx.guild.me.guild_permissions
        else:
            perms = ctx.channel.permissions_for(ctx.me)

        # commands.bot_has_guild_permissions doesn't test for this
        if perms.administrator:
            return True

        missing = [x for x in permissions if not getattr(perms, x)]

        if not missing:
            return True

        raise commands.BotMissingPermissions(missing)

    return commands.check(predicate)
