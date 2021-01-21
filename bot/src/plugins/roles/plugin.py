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

from ... import Plugin, bot_has_guild_permissions, bot_has_permissions, command
from ... import group as command_group
from ...utils import PaginatorInterface, code_safe
from .converter import Group


class Roles(Plugin):
    @command()
    @bot_has_permissions(send_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def join(self, ctx, group: Group):
        """
        Join a self-assignable group role.

        Group must be the full or partial name of the role.

        Example: `{prefix}join event announcements`
        """

        await ctx.author.add_roles(group, reason='Self-assigned role')
        await ctx.send(f'You\'ve been added to the `{code_safe(group)}` group.')

    @command()
    @bot_has_permissions(send_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def leave(self, ctx, group: Group):
        """
        Leave a self-assignable group role.

        Group must be the full or partial name of the role.

        Example: `{prefix}leave event announcements`
        """

        await ctx.author.remove_roles(group, reason='Self-assigned role')
        await ctx.send(f'You\'ve been removed from the `{code_safe(group)}` group.')

    @command_group()
    @bot_has_permissions(add_reactions=True, send_messages=True)
    async def groups(self, ctx):
        """
        Lists all available self-assignable group roles.

        Example: `{prefix}groups`
        """

        async with self.mousey.db.acquire() as conn:
            records = await conn.fetch('SELECT role_id, description FROM groups WHERE guild_id = $1', ctx.guild.id)

        if not records:
            await ctx.send('There are not self-assignable group roles set up.')
            return

        prefix = self.mousey.get_cog('Help').clean_prefix(ctx.prefix)

        join = f'{self.join.qualified_name} {self.join.signature}'
        leave = f'{self.leave.qualified_name} {self.leave.signature}'

        paginator = commands.Paginator(
            max_size=500,
            prefix='Self-assignable group roles:\n',
            suffix=f'\nUse `{prefix}{join}` and `{prefix}{leave}` to manage roles',
        )

        groups = []

        for record in records:
            role = ctx.guild.get_role(record['role_id'])

            if role is None:
                continue

            if not record['description']:
                description = ''
            else:
                description = ' - ' + record['description']

            groups.append(role.mention + description)

        groups.sort(key=str.lower)

        for group in groups:
            paginator.add_line(group)

        # TODO: https://github.com/Gorialis/jishaku/issues/87
        await PaginatorInterface(self.mousey, paginator, owner=ctx.author, timeout=600).send_to(ctx.channel)

    # TODO: Commands to create and delete groups
