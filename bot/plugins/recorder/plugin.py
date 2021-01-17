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

import collections
import datetime
import json
import logging

import discord

from ... import Plugin
from ...utils import code_safe, describe, describe_user, human_delta, user_name
from ..modlog import LogType
from .formatting import join_parts


log = logging.getLogger(__name__)


VS16 = '\N{VARIATION SELECTOR-16}'  # Required for some emoji to display


def enabled_permissions(permissions):
    for name, value in dict(permissions).items():
        if value:
            yield name.replace('_', ' ')


def moderator_info(moderator, reason):
    parts = []

    if reason is not None:
        parts.append(f'Reason: `{code_safe(reason)}`')

    if moderator is not None:
        parts.append(f'Performed By: `{describe_user(moderator)}`')

    return parts


def role_tag_info(role):
    if role.is_bot_managed():
        return 'Tags: Integrated bot role'

    if role.is_premium_subscriber():
        return 'Tags: Premium Subscriber role'

    if role.is_integration():
        return f'Tags: Managed by integration `{role.tags.integration_id}`'


class Recorder(Plugin):
    """Records events using the ModLog."""

    def log(self, *args, **kwargs):
        return self.mousey.get_cog('ModLog').log(*args, **kwargs)

    # Bot events

    @Plugin.listener()
    async def on_command_completion(self, ctx):
        user = ctx.author
        command = ctx.command.qualified_name

        msg = f'\N{CLIPBOARD} `{describe_user(user)}` used `{command}` in `{ctx.channel}` {user.mention}'
        await self.log(ctx.guild, LogType.COMMAND_USED, msg, target=ctx.author)

    # Discord events

    @Plugin.listener()
    async def on_mouse_member_join(self, member, moderator, reason):
        parts = []
        now = datetime.datetime.utcnow()

        seconds = (now - member.created_at).total_seconds()
        parts.append(f'Created `{human_delta(seconds)}` ago')

        if member.bot:
            verb = 'added'
            parts.extend(moderator_info(moderator, reason))
        else:
            verb = 'joined'

            tracking = self.mousey.get_cog('Tracking')
            removed_at = await tracking.get_removed_at(member)

            if removed_at is not None:
                seconds = (now - removed_at).total_seconds()

                if seconds < 86400 * 7:
                    parts.insert(0, f'Left `{human_delta(seconds)}` ago')
                else:
                    parts.insert(0, f'Left on ' + removed_at.strftime('`[%Y-%m-%d]`'))

        msg = f'\N{INBOX TRAY} `{describe_user(member)}` {verb} {member.mention}{join_parts(parts)}'
        await self.log(member.guild, LogType.MEMBER_JOIN, msg, target=member)

    @Plugin.listener()
    async def on_member_remove(self, member):
        parts = []

        now = datetime.datetime.utcnow()

        if member.joined_at is not None:
            seconds = (now - member.joined_at).total_seconds()

            joined_at = f'Joined `{human_delta(seconds)}` ago'
            bounced = '\N{BASKETBALL AND HOOP}' if seconds < 60 * 15 else ''

            parts.append(f'{joined_at} {bounced}')

        seen = await self.mousey.get_cog('Tracking').get_last_status(member)

        if seen.spoke is not None:
            seconds = (now - seen.spoke).total_seconds()
            parts.append(f'Last spoke `{human_delta(seconds)}` ago')

        count = len(member.roles)

        if count > 1:  # Members always have the @everyone role
            roles = ', '.join(f'`{code_safe(x)}`' for x in member.roles[10:0:-1])
            too_many = ', \N{HORIZONTAL ELLIPSIS}' if len(member.roles) > 11 else ''

            parts.append(f'Roles: {roles}{too_many}')

        msg = f'\N{OUTBOX TRAY} `{describe_user(member)}` left {member.mention}{join_parts(parts)}'
        await self.log(member.guild, LogType.MEMBER_REMOVE, msg, target=discord.Object(id=member.id))

    @Plugin.listener()
    async def on_user_update(self, before, after):
        if before.name == after.name and before.discriminator == after.discriminator:
            return

        msg = (
            f'\N{PENCIL}{VS16} `{describe_user(after)}` '
            f'changed name from `{user_name(before)}` to `{user_name(after)}` {after.mention}'
        )

        for guild in self.mousey.guilds:
            member = guild.get_member(after.id)

            if member is not None:
                await self.log(guild, LogType.MEMBER_NAME_CHANGE, msg, target=member)

    @Plugin.listener()
    async def on_mouse_nick_change(self, member, before, after, moderator, reason):
        if before is None:
            verb = 'added'
            changes = f'`{code_safe(after)}`'
        elif after is None:
            verb = 'removed'
            changes = f'`{code_safe(before)}`'
        else:
            verb = 'changed'
            changes = f'from `{code_safe(before)}` to `{code_safe(after)}`'

        if moderator == member:
            parts = []
        else:
            parts = moderator_info(moderator, reason)

        msg = (
            f'\N{LOWER LEFT BALLPOINT PEN} `{describe_user(member)}` '
            f'{verb} nick {changes} {member.mention}{join_parts(parts)}'
        )

        await self.log(member.guild, LogType.MEMBER_NICK_CHANGE, msg, target=member)

    @Plugin.listener()
    async def on_mouse_role_add(self, member, role, moderator, reason):
        parts = moderator_info(moderator, reason)

        if role.tags is not None:
            parts.append(role_tag_info(role))

        msg = (
            f'\N{GREEN BOOK} `{describe_user(member)}` added '
            f'role `{code_safe(role)}` {member.mention}{join_parts(parts)}'
        )

        await self.log(member.guild, LogType.MEMBER_ROLE_ADD, msg.strip(), target=member)

    @Plugin.listener()
    async def on_mouse_role_remove(self, member, role, moderator, reason):
        parts = []

        if member.guild.get_role(role.id) is None:
            parts.append(f'Reason: Role was deleted')
        else:
            if role.tags is not None:
                parts.append(role_tag_info(role))

            parts.extend(moderator_info(moderator, reason))

        msg = (
            f'\N{CLOSED BOOK} `{describe_user(member)}` removed '
            f'role `{code_safe(role)}` {member.mention}{join_parts(parts)}'
        )

        await self.log(member.guild, LogType.MEMBER_ROLE_REMOVE, msg.strip(), target=member)

    @Plugin.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None:
            event = LogType.MEMBER_VOICE_JOIN
            emoji = f'\N{STUDIO MICROPHONE}{VS16}'

            action = f'connected to `{code_safe(after.channel)}`'
        elif after.channel is None:
            event = LogType.MEMBER_VOICE_REMOVE
            emoji = f'\N{BLACK TELEPHONE}{VS16}'

            action = f'disconnected from `{code_safe(before.channel)}`'
        elif before.channel != after.channel:
            event = LogType.MEMBER_VOICE_MOVE
            emoji = f'\N{LEVEL SLIDER}{VS16}'

            action = f'moved from `{code_safe(before.channel)}` to `{code_safe(after.channel)}`'
        else:
            return  # Member is now muted / deafened etc. Don't log this for now.

        msg = f'{emoji} `{describe_user(member)}` {action} {member.mention}'
        await self.log(member.guild, event, msg, target=member)

    @Plugin.listener()
    async def on_mouse_member_kick(self, guild, member, moderator, reason):
        parts = moderator_info(moderator, reason)
        msg = f'\N{DOOR} `{describe_user(member)}` kicked {member.mention}{join_parts(parts)}'

        await self.log(guild, LogType.MEMBER_KICK, msg, target=discord.Object(id=member.id))

    @Plugin.listener()
    async def on_mouse_member_ban(self, guild, user, moderator, reason):
        parts = moderator_info(moderator, reason)
        msg = f'\N{HAMMER} `{describe_user(user)}` banned {user.mention}{join_parts(parts)}'

        await self.log(guild, LogType.MEMBER_BAN, msg, target=discord.Object(id=user.id))

    @Plugin.listener()
    async def on_mouse_member_unban(self, guild, user, moderator, reason):
        parts = moderator_info(moderator, reason)
        msg = f'\N{SPARKLES} `{describe_user(user)}` unbanned {user.mention}{join_parts(parts)}'

        await self.log(guild, LogType.MEMBER_UNBAN, msg, target=user)

    @Plugin.listener()
    async def on_mouse_role_create(self, role, moderator, reason):
        parts = []

        if role.tags is not None:
            parts.append(role_tag_info(role))

        if role.permissions.value:
            parts.append(f'Permissions: ' + ', '.join(f'`{x}`' for x in enabled_permissions(role.permissions)))

        parts.extend(moderator_info(moderator, reason))
        msg = f'\N{OPEN BOOK} `{describe(role)}` created{join_parts(parts)}'

        await self.log(role.guild, LogType.ROLE_DELETE, msg)

    @Plugin.listener()
    async def on_mouse_role_mentionable_update(self, role, before, after, moderator, reason):
        parts = moderator_info(moderator, reason)

        if after:
            msg = f'\N{BOOKS} `{describe(role)}` can now be mentioned{join_parts(parts)}'
        else:
            msg = f'\N{BOOKS} `{describe(role)}` can no longer be mentioned{join_parts(parts)}'

        await self.log(role.guild, LogType.ROLE_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_role_name_update(self, role, before, after, moderator, reason):
        parts = moderator_info(moderator, reason)

        msg = (
            f'\N{BOOKS} `{describe(role)}` renamed from '
            f'`{code_safe(before)}` to `{code_safe(after)}`{join_parts(parts)}'
        )

        await self.log(role.guild, LogType.ROLE_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_role_permissions_update(self, role, before, after, moderator, reason):
        common = before.value & after.value

        added = discord.Permissions(after.value ^ common)
        removed = discord.Permissions(before.value ^ common)

        parts = []

        if added.value:
            parts.append(f'Added: ' + ', '.join(f'`{x}`' for x in enabled_permissions(added)))
        if removed.value:
            parts.append(f'Removed: ' + ', '.join(f'`{x}`' for x in enabled_permissions(removed)))

        parts.extend(moderator_info(moderator, reason))

        msg = f'\N{BOOKS} `{describe(role)}` permissions updated{join_parts(parts)}'
        await self.log(role.guild, LogType.ROLE_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_role_delete(self, role, moderator, reason):
        parts = moderator_info(moderator, reason)

        if role.tags is not None:
            parts.append(role_tag_info(role))

        msg = f'\N{FILE CABINET}{VS16} `{describe(role)}` deleted{join_parts(parts)}'

        await self.log(role.guild, LogType.ROLE_DELETE, msg)

    @Plugin.listener()
    async def on_mouse_channel_create(self, channel, moderator, reason):
        parts = moderator_info(moderator, reason)
        msg = f'\N{PAGE FACING UP} `#{describe(channel)}` created{join_parts(parts)}'

        await self.log(channel.guild, LogType.CHANNEL_CREATE, msg)

    @Plugin.listener()
    async def on_mouse_channel_name_update(self, channel, before, after, moderator, reason):
        parts = moderator_info(moderator, reason)

        msg = (
            f'\N{PAPERCLIP} `#{describe(channel)}` renamed from '
            f'`{code_safe(before)}` to `{code_safe(after)}`{join_parts(parts)}'
        )

        await self.log(channel.guild, LogType.CHANNEL_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_channel_slowmode_delay_update(self, channel, before, after, moderator, reason):
        parts = moderator_info(moderator, reason)

        msg = (
            f'\N{PAPERCLIP} `#{describe(channel)}` slowmode changed from '
            f'`{human_delta(before)}` to `{human_delta(after)}`{join_parts(parts)}'
        )

        await self.log(channel.guild, LogType.CHANNEL_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_channel_delete(self, channel, moderator, reason):
        parts = moderator_info(moderator, reason)
        msg = f'\N{WASTEBASKET} `#{describe(channel)}` deleted{join_parts(parts)}'

        await self.log(channel.guild, LogType.CHANNEL_DELETE, msg)

    @Plugin.listener()
    async def on_mouse_message_edit(self, before, after):
        if after.author.id == self.mousey.user.id:
            return

        ...  # TODO

    @Plugin.listener()
    async def on_mouse_message_delete(self, message):
        if message.author.id == self.mousey.user.id:
            return

        ...  # TODO

    @Plugin.listener()
    async def on_mouse_bulk_message_delete(self, messages, archive_url):
        users = collections.Counter()

        for message in messages:
            users[message.author] += 1

        def fmt_author(data):
            author, count = data
            return f'`{describe_user(author)}` ({count})'

        authors = ', '.join(map(fmt_author, users.most_common(3)))

        parts = [
            f'Archive: <{archive_url}>',
            f'Authors: {authors}' + (', \N{HORIZONTAL ELLIPSIS}' if len(users) > 3 else ''),
        ]

        msg = (
            f'\N{PUT LITTER IN ITS PLACE SYMBOL} '
            f'{len(messages)} messages deleted in `#{messages[0].channel}`{join_parts(parts)}'
        )

        await self.log(messages[0].guild, LogType.MESSAGE_BULK_DELETE, msg)
