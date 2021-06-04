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


class _AttributedEvent:
    __slots__ = ('moderator', 'reason')

    def __init__(self, moderator, reason):
        self.moderator = moderator
        self.reason = reason

    @classmethod
    def from_entry(cls, *args, entry):
        if entry is None:
            # noinspection PyArgumentList
            return cls(*args, moderator=None, reason=None)
        else:
            # noinspection PyArgumentList
            return cls(*args, moderator=entry.user, reason=entry.reason)


# mouse_config_update
class ConfigUpdateEvent:
    __slots__ = ('guild',)

    def __init__(self, guild):
        self.guild = guild

    @property
    def key(self):
        return (self.guild.id,)


# mouse_guild_join
# mouse_guild_remove
class GuildChangeEvent:
    __slots__ = ('guild',)

    def __init__(self, guild):
        self.guild = guild

    @property
    def key(self):
        return (self.guild.id,)


# mouse_member_join
class MemberJoinEvent(_AttributedEvent):
    __slots__ = ('member',)

    def __init__(self, member, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.member = member

    @property
    def key(self):
        return (self.member.id,)


# mouse_nick_change
class MemberUpdateEvent(_AttributedEvent):
    __slots__ = ('member', 'before', 'after')

    def __init__(self, member, before, after, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.member = member

        self.before = before
        self.after = after

    @property
    def key(self):
        return (self.member.id,)


# mouse_role_add
# mouse_role_remove
class MemberRoleChangeEvent(_AttributedEvent):
    __slots__ = ('member', 'role')

    def __init__(self, member, role, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.member = member
        self.role = role

    @property
    def key(self):
        return self.member.id, self.role.id


# mouse_member_warn
# mouse_member_mute
# mouse_member_unmute
# mouse_member_kick
# mouse_member_ban
# mouse_member_unban
class InfractionEvent(_AttributedEvent):
    __slots__ = ('guild', 'user')

    def __init__(self, guild, user, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.guild = guild
        self.user = user

    @property
    def key(self):
        return self.guild.id, self.user.id


# mouse_role_create
# mouse_role_delete
class RoleChangeEvent(_AttributedEvent):
    __slots__ = ('role',)

    def __init__(self, role, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.role = role

    @property
    def key(self):
        return (self.role.id,)


# mouse_role_name_update
# mouse_role_permissions_update
# mouse_role_mentionable_update
class RoleUpdateEvent(_AttributedEvent):
    __slots__ = ('role', 'before', 'after')

    def __init__(self, role, before, after, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.role = role

        self.before = before
        self.after = after

    @property
    def key(self):
        return (self.role.id,)


# mouse_channel_create
# mouse_channel_delete
class ChannelChangeEvent(_AttributedEvent):
    __slots__ = ('channel',)

    def __init__(self, channel, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.channel = channel

    @property
    def key(self):
        return (self.channel.id,)


# mouse_channel_name_update
class ChannelUpdateEvent(_AttributedEvent):
    __slots__ = ('channel', 'before', 'after')

    def __init__(self, channel, before, after, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.channel = channel

        self.before = before
        self.after = after

    @property
    def key(self):
        return (self.channel.id,)


# mouse_message_edit
class MessageEditEvent:
    __slots__ = ('before', 'after')

    def __init__(self, before, after):
        self.before = before
        self.after = after


# mouse_message_delete
class MessageDeleteEvent(_AttributedEvent):
    __slots__ = ('message',)

    def __init__(self, message, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.message = message


# mouse_bulk_message_delete
class BulkMessageDeleteEvent(_AttributedEvent):
    __slots__ = ('messages', 'archive_url')

    def __init__(self, messages, archive_url, moderator=None, reason=None):
        super().__init__(moderator, reason)

        self.messages = messages
        self.archive_url = archive_url
