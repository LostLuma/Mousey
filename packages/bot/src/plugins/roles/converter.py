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

from ... import NotFound


def group_description(argument):
    if len(argument) <= 250:
        return argument

    raise commands.BadArgument('Description must be 250 or fewer characters.')


class Group(commands.Converter):
    async def convert(self, ctx, argument):
        name = argument.lower()

        try:
            resp = await ctx.bot.api.get_groups(ctx.guild.id)
        except NotFound:
            resp = []

        roles = (ctx.guild.get_role(x['role_id']) for x in resp)
        roles = sorted(filter(None, roles), key=lambda x: len(x.name))

        found = discord.utils.find(lambda x: name in x.name.lower(), roles)

        if found is not None:
            return found

        raise commands.BadArgument(f'Group "{argument}" not found.')
