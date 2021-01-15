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

import discord

from ... import Plugin
from ...utils import create_task


def after_has_role(role_id):
    def check(entry):
        return any(x.id == role_id for x in entry.after.roles)

    return check


def before_has_role(role_id):
    def check(entry):
        return any(x.id == role_id for x in entry.before.roles)

    return check


def match_attrs(name, before, after):
    def check(entry):
        return getattr(entry.before, name, None) == before and getattr(entry.after, name, None) == after

    return check


class Events(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self._ignored = set()

    def ignore(self, guild, event, *identifier):
        key = (guild.id, 'mouse_' + event, *identifier)

        self._ignored.add(key)
        asyncio.get_event_loop().call_later(15, self._ignored.discard, key)

    def _is_ignored(self, guild, event, *identifier):
        return (guild.id, event, *identifier) in self._ignored

    @Plugin.listener()
    async def on_member_join(self, member):
        # Bots or members joining via oauth may come with roles
        # Currently there is no way of fetching the application

        # Create a list here before the member could be updated
        roles = [x for x in member.roles if not x.is_default()]

        if not member.bot:
            entry = None
        else:
            audit_log = self.mousey.get_cog('AuditLog')
            entry = await audit_log.get_entry(member.guild, discord.AuditLogAction.bot_add, target=member)

        self._dispatch_from_entry('mouse_member_join', entry, member)

        for role in roles:
            self.mousey.dispatch('mouse_role_add', member, role, None, None)

    @Plugin.listener('on_member_update')
    async def on_member_nick_update(self, before, after):
        if before.nick == after.nick:
            return

        action = discord.AuditLogAction.member_update
        check = match_attrs('nick', before.nick, after.nick)

        await self._fetch_and_dispatch(
            after.guild, 'mouse_nick_change', action, after, after, before.nick, after.nick, check=check
        )

    @Plugin.listener('on_member_update')
    async def on_member_roles_update(self, before, after):
        if before.roles == after.roles:
            return

        old = set(before.roles)
        diff = old.symmetric_difference(set(after.roles))

        # We only need to look up the audit log entry here once,
        # However I think this approach is more readable (and smaller!)
        for role in diff:
            if role not in old:
                event = 'mouse_role_add'
                check = after_has_role(role.id)
            else:
                event = 'mouse_role_remove'
                check = before_has_role(role.id)

            if role.managed:
                self.mousey.dispatch(event, after, role, None, None)
            else:
                action = discord.AuditLogAction.member_role_update
                create_task(self._fetch_and_dispatch(after.guild, event, action, after, after, role, check=check))

    @Plugin.listener()
    async def on_member_remove(self, member):
        if member.id != self.mousey.user.id:
            guild = member.guild
            action = discord.AuditLogAction.kick

            task = create_task(
                self._fetch_and_dispatch(guild, 'mouse_member_kick', action, member, guild, member, required=True)
            )

            # In case the ban event is dispatched after the member is removed
            try:
                await self.mousey.wait_for(
                    'member_ban', check=lambda g, u: g.id == member.guild.id and u.id == member.id, timeout=8
                )
            except asyncio.TimeoutError:
                return

            task.cancel()  # Stop the AuditLog Plugin from further looking for information

    @Plugin.listener()
    async def on_member_ban(self, guild, user):
        # Most of the time this event is dispatched before member remove
        # Which means we can avoid looking up audit log entries for kicks
        self.ignore(guild, 'member_kick', guild, user)

        if user.id != self.mousey.user.id:
            await self._fetch_and_dispatch(guild, 'mouse_member_ban', discord.AuditLogAction.ban, user, guild, user)

    @Plugin.listener()
    async def on_member_unban(self, guild, user):
        await self._fetch_and_dispatch(guild, 'mouse_member_unban', discord.AuditLogAction.unban, user, guild, user)

    @Plugin.listener()
    async def on_guild_role_create(self, role):
        if role.managed:
            self.mousey.dispatch('mouse_role_create', role, None, None)
        else:
            await self._fetch_and_dispatch(
                role.guild, 'mouse_role_create', discord.AuditLogAction.role_create, role, role
            )

    @Plugin.listener()
    async def on_guild_role_update(self, before, after):
        attrs = ('mentionable', 'name', 'permissions')
        await self._compare_and_dispatch('role', discord.AuditLogAction.role_update, before, after, attrs)

    @Plugin.listener()
    async def on_guild_role_delete(self, role):
        if role.managed:
            self.mousey.dispatch('mouse_role_delete', role, None, None)
        else:
            await self._fetch_and_dispatch(
                role.guild, 'mouse_role_delete', discord.AuditLogAction.role_delete, role, role
            )

    @Plugin.listener()
    async def on_guild_channel_create(self, channel):
        await self._fetch_and_dispatch(
            channel.guild, 'mouse_channel_create', discord.AuditLogAction.channel_create, channel, channel
        )

    @Plugin.listener()
    async def on_guild_channel_update(self, before, after):
        attrs = ('name', 'slowmode_delay')
        await self._compare_and_dispatch('channel', discord.AuditLogAction.channel_update, before, after, attrs)

    @Plugin.listener()
    async def on_guild_channel_delete(self, channel):
        await self._fetch_and_dispatch(
            channel.guild, 'mouse_channel_delete', discord.AuditLogAction.channel_delete, channel, channel
        )

    async def _compare_and_dispatch(self, kind, action, before, after, attrs):
        for name in attrs:
            former = getattr(before, name, None)
            current = getattr(after, name, None)

            if former != current:
                # Eg. mouse_role_permissions_update
                event = f'mouse_{kind}_{name}_update'
                check = match_attrs(name, former, current)

                create_task(
                    self._fetch_and_dispatch(after.guild, event, action, after, after, former, current, check=check)
                )

    async def _fetch_and_dispatch(self, guild, event, action, target, *event_args, check=None, required=False):
        if self._is_ignored(guild, event, *event_args):
            return

        if action is discord.AuditLogAction.kick:
            timeout = 4
        else:
            timeout = 8

        audit_log = self.mousey.get_cog('AuditLog')
        entry = await audit_log.get_entry(guild, action, target=target, check=check, timeout=timeout)

        if entry is not None or not required:
            self._dispatch_from_entry(event, entry, *event_args)

    def _dispatch_from_entry(self, event, entry, *event_args):
        if entry is None:
            moderator, reason = None, None
        else:
            moderator, reason = entry.user, entry.reason

        self.mousey.dispatch(event, *event_args, moderator, reason)
