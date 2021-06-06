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

from ... import (
    HTTPException,
    LogType,
    MemberRoleChangeEvent,
    NotFound,
    Plugin,
    VisibleCommandError,
    bot_has_guild_permissions,
    bot_has_permissions,
    command,
)
from ... import group as command_group
from ...utils import PaginatorInterface, close_interface_context, code_safe, describe
from .converter import Group, group_description


PRIVILEGED_PERMISSIONS = discord.Permissions(
    administrator=True,
    ban_members=True,
    deafen_members=True,
    kick_members=True,
    manage_channels=True,
    manage_emojis=True,
    manage_guild=True,
    manage_messages=True,
    manage_nicknames=True,
    manage_roles=True,
    manage_webhooks=True,
    mention_everyone=True,
    move_members=True,
    mute_members=True,
)


def enabled_permissions(permissions):
    for name, value in dict(permissions).items():
        if value:
            yield name.replace('_', ' ')


class Roles(Plugin):
    @command()
    @bot_has_permissions(send_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def join(self, ctx, *, group: Group):
        """
        Join a self-assignable group role.
        You can view all group roles using `{prefix}groups`.

        Group must be the full or partial name of the role.

        Example: `{prefix}join event announcements`
        """

        await self._ensure_no_privileged_permissions(group)

        if group not in ctx.author.roles:
            reason = 'Self-assigned role'
            event = MemberRoleChangeEvent(ctx.author, group, ctx.me, reason)

            events = self.mousey.get_cog('Events')
            events.ignore(ctx.guild, 'mouse_role_add', event)

            await ctx.author.add_roles(group, reason=reason)
            self.mousey.dispatch('mouse_role_add', event)

        await ctx.send(f'You\'ve been added to the `{code_safe(group)}` group role.')

    @command()
    @bot_has_permissions(send_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def leave(self, ctx, *, group: Group):
        """
        Leave a self-assignable group role.
        You can view all group roles using `{prefix}groups`.

        Group must be the full or partial name of the role.

        Example: `{prefix}leave event announcements`
        """

        await self._ensure_no_privileged_permissions(group)

        if group in ctx.author.roles:
            reason = 'Self-assigned role'
            event = MemberRoleChangeEvent(ctx.author, group, ctx.me, reason)

            events = self.mousey.get_cog('Events')
            events.ignore(ctx.guild, 'mouse_role_remove', event)

            await ctx.author.remove_roles(group, reason=reason)
            self.mousey.dispatch('mouse_role_remove', event)

        await ctx.send(f'You\'ve been removed from the `{code_safe(group)}` group role.')

    async def _ensure_no_privileged_permissions(self, role):
        enabled = discord.Permissions(PRIVILEGED_PERMISSIONS.value & role.permissions.value)

        if not enabled.value:
            return

        msg = (
            f'\N{SHIELD} `{describe(role)}` is configured as a group role, but has privileged permissions\n'
            f'\N{BULLET} Conflicting permissions: ' + ', '.join(f'`{x}`' for x in enabled_permissions(enabled))
        )

        modlog = self.mousey.get_cog('ModLog')
        await modlog.log(role.guild, LogType.BOT_INFO, msg)

        raise VisibleCommandError(
            f'Unable to join group, the role "{role.name}" has dangerous permissions enabled.\n\n'
            f'Moderators can see exact details about conflicting permissions in the modlog, if enabled.'
        )

    @command_group(aliases=['group'])
    @bot_has_permissions(add_reactions=True, send_messages=True)
    async def groups(self, ctx):
        """
        Lists all available self-assignable group roles.

        Example: `{prefix}groups`
        """

        try:
            resp = await self.mousey.api.get_groups(ctx.guild.id)
        except NotFound:
            await ctx.send('There are no self-assignable group roles set up.')
            return

        prefix = self.mousey.get_cog('Help').clean_prefix(ctx.prefix)

        join = f'{self.join.qualified_name} {self.join.signature}'
        leave = f'{self.leave.qualified_name} {self.leave.signature}'

        paginator = commands.Paginator(
            max_size=1750,
            prefix='Self-assignable group roles:\n',
            suffix=f'\nUse `{prefix}{join}` and `{prefix}{leave}` to manage roles',
        )

        groups = {}

        for data in resp:
            role = ctx.guild.get_role(data['role_id'])

            if role is None:
                continue

            if not data['description']:
                description = ''
            else:
                description = ' - ' + data['description']

            groups[role.name] = role.mention + description

        # Display groups in alphanumerical order
        for name, description in sorted(groups.items(), key=lambda item: item[0].lower()):
            paginator.add_line(description)

        interface = PaginatorInterface(self.mousey, paginator, owner=ctx.author, timeout=600)

        await interface.send_to(ctx.channel)
        close_interface_context(ctx, interface)

    @groups.command('create')
    @commands.has_permissions(manage_roles=True)
    @bot_has_permissions(send_messages=True)
    async def groups_create(self, ctx, role: discord.Role, *, description: group_description = None):
        """
        Allow users to manage their role membership for a role using the `join` and `leave` commands.

        Role must be specified as a mention, ID, or name.
        Description can be any string up to 250 characters or will default to being empty.

        Example: `{prefix}groups create "LF Campaign" Receive notifications about new campaigns`
        """

        data = {'description': description}

        try:
            await self.mousey.api.create_group(ctx.guild.id, role.id, data)
        except HTTPException as e:
            await ctx.send(f'Failed to create group. {e.message}')  # Lists privileged permissions,,
        else:
            if description is None:
                extra = ''
            else:
                extra = f'with description `{code_safe(description)}`'

            await ctx.send(f'Created group `{code_safe(role)}`{extra}.')

    @groups.command('remove')
    @commands.has_permissions(manage_roles=True)
    @bot_has_permissions(send_messages=True)
    async def groups_remove(self, ctx, *, group: Group):
        """
        Remove a role from the self-assignable group role list.

        Group must be the full or partial name of the role.

        Example: `{prefix}group remove LF Campaign`
        """

        await self.mousey.api.delete_group(ctx.guild.id, group.id)
        await ctx.send(f'Successfully removed group `{code_safe(group)}`.')
