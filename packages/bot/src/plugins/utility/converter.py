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

import re

import discord
from discord.ext import commands


def info_category(categories):
    def converter(argument):
        if argument.lower() in categories:
            return argument.lower()

        valid = ', '.join(f'"{x}"' for x in categories)
        raise commands.BadArgument(f'Category must be done of {valid}, not "{argument}".')

    return converter


class MentionableRole(commands.Converter):
    async def convert(self, ctx, argument):
        match = re.match(r'(?:<@&)?(\d{15,21})>?', argument)

        if match is not None:
            role_id = int(match.group(1))
            role = ctx.guild.get_role(role_id)

            if self._is_editable(ctx, role):
                return role

        name = argument.lower()
        role = discord.utils.find(lambda x: x.name.lower() == name, ctx.guild.roles)

        if self._is_editable(ctx, role):
            return role

        raise commands.BadArgument(f'Role "{argument}" not found.')

    def _is_editable(self, ctx, role):
        if role is None:
            return False

        if not ctx.channel.permissions_for(ctx.me).mention_everyone and role >= ctx.me.top_role:
            raise commands.BadArgument(f'Role "{role.name}" is too high in the role hierarchy for me to edit.')

        if not ctx.channel.permissions_for(ctx.author).mention_everyone and role >= ctx.author.top_role:
            raise commands.BadArgument(f'Role "{role.name}" is too high in the role hierarchy for you to edit.')

        return True
