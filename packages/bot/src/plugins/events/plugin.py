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
import collections

import discord

from ... import Plugin
from ...events import (
    ChannelChangeEvent,
    ChannelUpdateEvent,
    EmojiChangeEvent,
    EmojiUpdateEvent,
    InfractionEvent,
    MemberJoinEvent,
    MemberRoleChangeEvent,
    MemberUpdateEvent,
    RoleChangeEvent,
    RoleUpdateEvent,
    ThreadChangeEvent,
    ThreadMemberChangeEvent,
    ThreadUpdateEvent,
)
from ...utils import call_later, create_task, set_none_result


KICK_TIMEOUT = 4
DEFAULT_TIMEOUT = 8

TEXT_CHANNEL_THREAD_TYPES = (
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
)


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

        # Events dispatched by the bot
        # Which can be ignored from the gateway
        self._ignored = set()

        # Table of recent mentions and recipient messages in threads
        # Used to look up who is responsible for adding / removing thread members
        self._thread_member_changes = {}

        # Pending tasks which are looking up thread membership information
        self._thread_member_lookups = collections.defaultdict(list)

    # Event helpers

    def ignore(self, guild, event_name, event):
        key = (guild.id, event_name, *event.key)

        self._ignored.add(key)
        call_later(5, self._ignored.discard, key)

    def is_ignored(self, guild, event_name, event):
        return (guild.id, event_name, *event.key) in self._ignored

    # Thread member helpers

    def _get_thread_member_change(self, thread, member, change):
        self._remove_expired_thread_member_lookups()

        future = asyncio.Future()
        call_later(2, set_none_result, future)

        for item in (member, *member.roles):
            key = (thread.id, item.id, change)

            if key in self._thread_member_changes:
                future.set_result(self._thread_member_changes[key])
            else:
                self._thread_member_lookups[key].append(future)

        return future

    def _remove_expired_thread_member_lookups(self):
        previous = self._thread_member_lookups
        self._thread_member_lookups = lookups = collections.defaultdict(list)

        for key, tasks in previous.items():
            if not all(x.done() for x in tasks):
                lookups[key] = tasks

    def _cache_thread_member_change(self, thread, member, moderator, change):
        key = (thread.id, member.id, change)

        if key in self._thread_member_lookups:
            for task in self._thread_member_lookups[key]:
                try:
                    task.set_result(moderator.id)
                except asyncio.InvalidStateError:
                    pass  # Future previously matched on another key
        else:
            self._thread_member_changes[key] = moderator.id
            call_later(2, self._remove_cached_thread_member_change, key)

    def _remove_cached_thread_member_change(self, key):
        try:
            del self._thread_member_changes[key]
        except KeyError:
            pass

    # Discord events

    @Plugin.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.type not in TEXT_CHANNEL_THREAD_TYPES:
            return

        if message.type is discord.MessageType.recipient_remove:
            change = 'remove'
        else:
            change = 'invite'

        for user in message.mentions:
            self._cache_thread_member_change(message.channel, user, message.author, change)

        for role in message.role_mentions:
            self._cache_thread_member_change(message.channel, role, message.author, change)

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

        self.mousey.dispatch('mouse_member_join', MemberJoinEvent.from_entry(member, entry=entry))

        for role in roles:
            self.mousey.dispatch('mouse_role_add', MemberRoleChangeEvent.from_entry(member, role, entry=entry))

    @Plugin.listener('on_member_update')
    async def on_member_nick_update(self, before, after):
        if before.nick == after.nick:
            return

        action = discord.AuditLogAction.member_update
        check = match_attrs('nick', before.nick, after.nick)

        event = MemberUpdateEvent(after, before.nick, after.nick)
        await self._fetch_and_dispatch(after.guild, 'mouse_nick_change', event, action, target=after, check=check)

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
                event_name = 'mouse_role_add'
                check = after_has_role(role.id)
            else:
                event_name = 'mouse_role_remove'
                check = before_has_role(role.id)

            event = MemberRoleChangeEvent(after, role)

            if role.managed:
                self.mousey.dispatch(event_name, event)
            else:
                action = discord.AuditLogAction.member_role_update
                create_task(self._fetch_and_dispatch(after.guild, event_name, event, action, target=after, check=check))

    @Plugin.listener()
    async def on_member_remove(self, member):
        if member.id == self.mousey.user.id:
            return

        action = discord.AuditLogAction.kick
        event = InfractionEvent(member.guild, member)

        task = create_task(
            self._fetch_and_dispatch(member.guild, 'mouse_member_kick', event, action, target=member, required=True)
        )

        # In case the ban event is dispatched after the member is removed
        try:
            await self.mousey.wait_for(
                'member_ban', check=lambda g, u: g.id == member.guild.id and u.id == member.id, timeout=KICK_TIMEOUT
            )
        except asyncio.TimeoutError:
            return

        task.cancel()  # Stop the AuditLog Plugin from further looking for information

    @Plugin.listener()
    async def on_member_ban(self, guild, user):
        if user.id == self.mousey.user.id:
            return

        event = InfractionEvent(guild, user)

        # Most of the time this event is dispatched before member remove
        # Which means we can avoid looking up audit log entries for kicks
        self.ignore(guild, 'mouse_member_kick', event)
        await self._fetch_and_dispatch(guild, 'mouse_member_ban', event, discord.AuditLogAction.ban, target=user)

    @Plugin.listener()
    async def on_member_unban(self, guild, user):
        event = InfractionEvent(guild, user)
        await self._fetch_and_dispatch(guild, 'mouse_member_unban', event, discord.AuditLogAction.unban, target=user)

    @Plugin.listener()
    async def on_guild_role_create(self, role):
        event = RoleChangeEvent(role)

        if role.managed:
            self.mousey.dispatch('mouse_role_create', event)
        else:
            await self._fetch_and_dispatch(
                role.guild, 'mouse_role_create', event, discord.AuditLogAction.role_create, target=role
            )

    @Plugin.listener()
    async def on_guild_role_update(self, before, after):
        attrs = ('color', 'mentionable', 'name', 'permissions')
        self._compare_and_dispatch(RoleUpdateEvent, 'role', discord.AuditLogAction.role_update, before, after, attrs)

    @Plugin.listener()
    async def on_guild_role_delete(self, role):
        event = RoleChangeEvent(role)

        if role.managed:
            self.mousey.dispatch('mouse_role_delete', event)
        else:
            await self._fetch_and_dispatch(
                role.guild, 'mouse_role_delete', event, discord.AuditLogAction.role_delete, target=role
            )

    @Plugin.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        old = {emoji.id: emoji for emoji in before}

        for emoji in after:
            before = old.get(emoji.id)

            if before is None:
                event = EmojiChangeEvent(emoji)
                event_name = 'mouse_emoji_create'

                action = discord.AuditLogAction.emoji_create
                await self._fetch_and_dispatch(guild, event_name, event, action, target=emoji)
            elif before.name != emoji.name:
                event = EmojiUpdateEvent(emoji, before.name, emoji.name)
                event_name = 'mouse_emoji_name_update'

                action = discord.AuditLogAction.emoji_update
                await self._fetch_and_dispatch(guild, event_name, event, action, target=emoji)

            try:
                del old[emoji.id]
            except KeyError:
                pass

        for emoji in old.values():
            event = EmojiChangeEvent(emoji)
            event_name = 'mouse_emoji_delete'

            action = discord.AuditLogAction.emoji_delete
            await self._fetch_and_dispatch(guild, event_name, event, action, target=emoji)

    @Plugin.listener()
    async def on_guild_channel_create(self, channel):
        event = ChannelChangeEvent(channel)

        await self._fetch_and_dispatch(
            channel.guild, 'mouse_channel_create', event, discord.AuditLogAction.channel_create, target=channel
        )

    @Plugin.listener()
    async def on_guild_channel_update(self, before, after):
        attrs = ('name', 'slowmode_delay')

        self._compare_and_dispatch(
            ChannelUpdateEvent, 'channel', discord.AuditLogAction.channel_update, before, after, attrs
        )

    @Plugin.listener()
    async def on_guild_channel_delete(self, channel):
        event = ChannelChangeEvent(channel)

        await self._fetch_and_dispatch(
            channel.guild, 'mouse_channel_delete', event, discord.AuditLogAction.channel_delete, target=channel
        )

    @Plugin.listener()
    async def on_thread_join(self, thread):
        # This event is dispatched in a few cases:
        # - A new thread is created
        # - An archived, uncached thread is unarchived
        # - The bot is added to an existing thread
        # We only want to log something in the first two cases.
        # This information can however only be retrieved via the audit log,
        # Meaning these two events will not work without permissions
        # Or during an edge case where no audit log event could be retrieved.
        futures = []

        options = (
            {'action': discord.AuditLogAction.thread_create},
            {'action': discord.AuditLogAction.thread_update, 'check': match_attrs('archived', True, False)},
        )

        for kwargs in options:
            audit_log = self.mousey.get_cog('AuditLog')
            futures.append(audit_log.get_entry(thread.guild, target=thread, **kwargs))

        done, pending = await asyncio.wait(futures, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

        entry = await next(iter(done))

        if entry is None:
            return  # Thread was neither joined or unarchived, duplicate event

        event = ThreadChangeEvent.from_entry(thread.guild, thread, entry=entry)

        if entry.action is discord.AuditLogAction.thread_update:
            event_name = 'mouse_thread_unarchive'
        else:
            event_name = 'mouse_thread_create'

            # If the bot joins the thread right away we receive
            # A duplicate thread join event with audit log entry
            if self.is_ignored(thread.guild, event_name, event):
                return

            self.ignore(thread.guild, event_name, event)

        self.mousey.dispatch(event_name, event)

    @Plugin.listener()
    async def on_thread_member_join(self, member):
        guild = member.thread.guild
        guild_member = guild.get_member(member.id)

        if guild_member is None:
            moderator = None
        else:
            moderator_id = await self._get_thread_member_change(member.thread, guild_member, 'invite')
            moderator = member.thread.guild.get_member(moderator_id)

        event = ThreadMemberChangeEvent(member, moderator)
        self.mousey.dispatch('mouse_thread_member_join', event)

    @Plugin.listener()
    async def on_thread_update(self, before, after):
        if before.name == after.name and before.archived == after.archived:
            return

        audit_log = self.mousey.get_cog('AuditLog')

        if before.archived != after.archived:
            check = match_attrs('archived', before.archived, after.archived)
            entry = await audit_log.get_entry(
                before.guild, discord.AuditLogAction.thread_update, target=before, check=check
            )

            if not before.archived:
                event_name = 'mouse_thread_archive'
            else:
                event_name = 'mouse_thread_unarchive'

            event = ThreadChangeEvent.from_entry(after.guild, after, entry=entry)
        else:
            check = match_attrs('name', before.name, after.name)
            entry = await audit_log.get_entry(
                before.guild, discord.AuditLogAction.thread_update, target=before, check=check
            )

            event_name = 'mouse_thread_name_update'
            event = ThreadUpdateEvent.from_entry(before, before, after, entry=entry)

        self.mousey.dispatch(event_name, event)

    @Plugin.listener()
    async def on_thread_member_remove(self, member):
        guild = member.thread.guild
        guild_member = guild.get_member(member.id)

        if guild_member is None:
            moderator = None
        else:
            moderator_id = await self._get_thread_member_change(member.thread, guild_member, 'remove')
            moderator = member.thread.guild.get_member(moderator_id)

        event = ThreadMemberChangeEvent(member, moderator)
        self.mousey.dispatch('mouse_thread_member_remove', event)

    @Plugin.listener()
    async def on_raw_thread_delete(self, payload):
        guild = self.mousey.get_guild(payload.guild_id)
        event = ThreadChangeEvent(guild, payload.thread or discord.Object(payload.thread_id))

        await self._fetch_and_dispatch(
            guild, 'mouse_thread_delete', event, discord.AuditLogAction.thread_delete, target=event.thread
        )

    def _compare_and_dispatch(self, cls, kind, action, before, after, attrs):
        for name in attrs:
            former = getattr(before, name, None)
            current = getattr(after, name, None)

            if former != current:
                event = cls(after, former, current)
                # Eg. mouse_role_permissions_update
                event_name = f'mouse_{kind}_{name}_update'

                check = match_attrs(name, former, current)

                create_task(self._fetch_and_dispatch(after.guild, event_name, event, action, target=after, check=check))

    async def _fetch_and_dispatch(self, guild, event_name, event, action, *, target=None, check=None, required=False):
        if self.is_ignored(guild, event_name, event):
            return

        if action is discord.AuditLogAction.kick:
            timeout = KICK_TIMEOUT
        else:
            timeout = DEFAULT_TIMEOUT

        audit_log = self.mousey.get_cog('AuditLog')
        entry = await audit_log.get_entry(guild, action, target=target, check=check, timeout=timeout)

        if entry is not None:
            event.reason = entry.reason
            event.moderator = entry.user

            self.mousey.dispatch(event_name, event)
        elif not required:
            self.mousey.dispatch(event_name, event)

    # Bot events

    @Plugin.listener()
    async def on_mouse_role_add(self, event):
        if self.is_ignored(event.member.guild, 'mouse_role_add', event):
            return

        if not await self._is_mute_role(event.role):
            return

        self.mousey.dispatch(
            'mouse_member_mute', InfractionEvent(event.member.guild, event.member, event.moderator, event.reason)
        )

    @Plugin.listener()
    async def on_mouse_role_remove(self, event):
        if self.is_ignored(event.member.guild, 'mouse_role_remove', event):
            return

        if not await self._is_mute_role(event.role):
            return

        self.mousey.dispatch(
            'mouse_member_unmute', InfractionEvent(event.member.guild, event.member, event.moderator, event.reason)
        )

    async def _is_mute_role(self, role):
        moderation = self.mousey.get_cog('Moderation')
        return await moderation.get_mute_role(role.guild) == role
