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

from ... import LogType, Plugin
from ...utils import Plural, code_safe, create_paste, describe, describe_user, human_delta, user_name
from .formatting import describe_emoji, escape_formatting, indent_multiline, join_parts, join_with_code


log = logging.getLogger(__name__)


VS16 = '\N{VARIATION SELECTOR-16}'  # Required for some emoji to display


def enabled_permissions(permissions):
    for name, value in dict(permissions).items():
        if value:
            yield name.replace('_', ' ')


def moderator_info(event):
    parts = []

    if event.reason is not None:
        parts.append(f'Reason: `{code_safe(event.reason)}`')

    if event.moderator is not None:
        parts.append(f'Performed By: `{describe_user(event.moderator)}`')

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
    async def on_mouse_member_join(self, event):
        parts = []
        now = discord.utils.utcnow()

        seconds = (now - event.member.created_at).total_seconds()

        is_new = '\N{SQUARED NEW}' if seconds < 86400 * 7 else ''
        parts.append(f'Created `{human_delta(seconds)}` ago {is_new}')

        if event.member.bot:
            verb = 'added'
            parts.extend(moderator_info(event))
        else:
            verb = 'joined'

            tracking = self.mousey.get_cog('Tracking')
            removed_at = await tracking.get_removed_at(event.member)

            if removed_at is not None:
                now = datetime.datetime.utcnow()
                seconds = (now - removed_at).total_seconds()

                if seconds < 86400 * 7:
                    parts.insert(0, f'Left `{human_delta(seconds)}` ago')
                else:
                    parts.insert(0, f'Left on ' + removed_at.strftime('`%Y-%m-%d`'))

        msg = f'\N{INBOX TRAY} `{describe_user(event.member)}` {verb} {event.member.mention}{join_parts(parts)}'
        await self.log(event.member.guild, LogType.MEMBER_JOIN, msg, target=event.member)

    @Plugin.listener()
    async def on_member_remove(self, member):
        parts = []

        if member.joined_at is not None:
            now = discord.utils.utcnow()
            seconds = (now - member.joined_at).total_seconds()

            joined_at = f'Joined `{human_delta(seconds)}` ago'
            bounced = '\N{BASKETBALL AND HOOP}' if seconds < 60 * 15 else ''

            parts.append(f'{joined_at} {bounced}')

        if member.pending:
            parts.append(f'Pending: Has not passed membership screening')

        count = len(member.roles)

        if count > 1:  # Members always have the @everyone role
            roles = join_with_code(member.roles[10:0:-1])
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
    async def on_mouse_nick_change(self, event):
        if event.before is None:
            verb = 'added'
            changes = f'`{code_safe(event.after)}`'
        elif event.after is None:
            verb = 'removed'
            changes = f'`{code_safe(event.before)}`'
        else:
            verb = 'changed'
            changes = f'from `{code_safe(event.before)}` to `{code_safe(event.after)}`'

        if event.moderator == event.member:
            parts = []
        else:
            parts = moderator_info(event)

        msg = (
            f'\N{LOWER LEFT BALLPOINT PEN} `{describe_user(event.member)}` '
            f'{verb} nick {changes} {event.member.mention}{join_parts(parts)}'
        )

        await self.log(event.member.guild, LogType.MEMBER_NICK_CHANGE, msg, target=event.member)

    @Plugin.listener()
    async def on_member_update(self, before, after):
        if before.pending == after.pending:
            return

        msg = (
            f'\N{LEFT-POINTING MAGNIFYING GLASS} '
            f'`{describe_user(after)}` completed membership screening {after.mention}'
        )

        await self.log(after.guild, LogType.MEMBER_SCREENING_COMPLETE, msg, target=after)

    @Plugin.listener()
    async def on_mouse_role_add(self, event):
        parts = moderator_info(event)

        if event.role.tags is not None:
            parts.append(role_tag_info(event.role))

        msg = (
            f'\N{GREEN BOOK} `{describe_user(event.member)}` added '
            f'role `{code_safe(event.role)}` {event.member.mention}{join_parts(parts)}'
        )

        await self.log(event.member.guild, LogType.MEMBER_ROLE_ADD, msg.strip(), target=event.member)

    @Plugin.listener()
    async def on_mouse_role_remove(self, event):
        parts = []

        if event.member.guild.get_role(event.role.id) is None:
            parts.append(f'Reason: Role was deleted')
        else:
            if event.role.tags is not None:
                parts.append(role_tag_info(event.role))

            parts.extend(moderator_info(event))

        msg = (
            f'\N{CLOSED BOOK} `{describe_user(event.member)}` removed '
            f'role `{code_safe(event.role)}` {event.member.mention}{join_parts(parts)}'
        )

        await self.log(event.member.guild, LogType.MEMBER_ROLE_REMOVE, msg.strip(), target=event.member)

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
    async def on_mouse_member_warn(self, event):
        parts = moderator_info(event)

        msg = (
            f'\N{ROLLED-UP NEWSPAPER}{VS16} '
            f'`{describe_user(event.user)}` was warned {event.user.mention}{join_parts(parts)}'
        )

        await self.log(event.guild, LogType.MEMBER_WARN, msg, target=event.user)

    @Plugin.listener()
    async def on_mouse_member_mute(self, event):
        parts = moderator_info(event)

        msg = (
            f'\N{SPEAKER WITH CANCELLATION STROKE} '
            f'`{describe_user(event.user)}` was muted {event.user.mention}{join_parts(parts)}'
        )

        await self.log(event.guild, LogType.MEMBER_MUTE, msg, target=event.user)

    @Plugin.listener()
    async def on_mouse_member_unmute(self, event):
        parts = moderator_info(event)

        msg = (
            f'\N{SPEAKER WITH THREE SOUND WAVES} '
            f'`{describe_user(event.user)}` was unmuted {event.user.mention}{join_parts(parts)}'
        )

        await self.log(event.guild, LogType.MEMBER_UNMUTE, msg, target=event.user)

    @Plugin.listener()
    async def on_mouse_member_kick(self, event):
        parts = moderator_info(event)
        msg = f'\N{DOOR} `{describe_user(event.user)}` was kicked {event.user.mention}{join_parts(parts)}'

        await self.log(event.guild, LogType.MEMBER_KICK, msg, target=discord.Object(id=event.user.id))

    @Plugin.listener()
    async def on_mouse_member_ban(self, event):
        parts = moderator_info(event)
        msg = f'\N{HAMMER} `{describe_user(event.user)}` was banned {event.user.mention}{join_parts(parts)}'

        await self.log(event.guild, LogType.MEMBER_BAN, msg, target=discord.Object(id=event.user.id))

    @Plugin.listener()
    async def on_mouse_member_unban(self, event):
        parts = moderator_info(event)
        msg = f'\N{SPARKLES} `{describe_user(event.user)}` was unbanned {event.user.mention}{join_parts(parts)}'

        await self.log(event.guild, LogType.MEMBER_UNBAN, msg, target=event.user)

    @Plugin.listener()
    async def on_mouse_role_create(self, event):
        parts = []

        if event.role.tags is not None:
            parts.append(role_tag_info(event.role))

        if event.role.permissions.value:
            parts.append(f'Permissions: ' + join_with_code(enabled_permissions(event.role.permissions)))

        parts.extend(moderator_info(event))
        msg = f'\N{OPEN BOOK} `{describe(event.role)}` created{join_parts(parts)}'

        await self.log(event.role.guild, LogType.ROLE_DELETE, msg)

    @Plugin.listener()
    async def on_mouse_role_color_update(self, event):
        parts = moderator_info(event)

        msg = (
            f'\N{LOWER LEFT PAINTBRUSH}{VS16} `{describe(event.role)}` color updated from '
            f'`#{hex(event.before.value)[2:]}` to `#{hex(event.after.value)[2:]}`{join_parts(parts)}'
        )

        await self.log(event.role.guild, LogType.ROLE_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_role_name_update(self, event):
        parts = moderator_info(event)

        msg = (
            f'\N{BOOKS} `{describe(event.role)}` was renamed from '
            f'`{code_safe(event.before)}` to `{code_safe(event.after)}`{join_parts(parts)}'
        )

        await self.log(event.role.guild, LogType.ROLE_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_role_mentionable_update(self, event):
        parts = moderator_info(event)

        if event.after:
            msg = f'\N{BOOKS} `{describe(event.role)}` can now be mentioned{join_parts(parts)}'
        else:
            msg = f'\N{BOOKS} `{describe(event.role)}` can no longer be mentioned{join_parts(parts)}'

        await self.log(event.role.guild, LogType.ROLE_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_role_permissions_update(self, event):
        common = event.before.value & event.after.value

        added = discord.Permissions(event.after.value ^ common)
        removed = discord.Permissions(event.before.value ^ common)

        parts = []

        if added.value:
            parts.append(f'Added: ' + join_with_code(enabled_permissions(added)))
        if removed.value:
            parts.append(f'Removed: ' + join_with_code(enabled_permissions(removed)))

        parts.extend(moderator_info(event))

        msg = f'\N{BOOKS} `{describe(event.role)}` permissions updated{join_parts(parts)}'
        await self.log(event.role.guild, LogType.ROLE_PERMISSIONS_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_role_delete(self, event):
        parts = moderator_info(event)

        if event.role.tags is not None:
            parts.append(role_tag_info(event.role))

        msg = f'\N{FILE CABINET}{VS16} `{describe(event.role)}` deleted{join_parts(parts)}'

        await self.log(event.role.guild, LogType.ROLE_DELETE, msg)

    @Plugin.listener()
    async def on_mouse_emoji_create(self, event):
        parts = moderator_info(event)
        parts.append(f'Emoji URL: <{event.emoji.url}>')

        msg = f'\N{ARTIST PALETTE} `{describe_emoji(event.emoji)}` was uploaded{join_parts(parts)}'
        await self.log(event.emoji.guild, LogType.EMOJI_CREATE, msg)

    @Plugin.listener()
    async def on_mouse_emoji_name_update(self, event):
        parts = moderator_info(event)
        parts.append(f'Emoji URL: <{event.emoji.url}>')

        msg = (
            f'\N{BOOKS} `{describe_emoji(event.emoji)}` was renamed from '
            f'`{code_safe(event.before)}` to `{code_safe(event.after)}`{join_parts(parts)}'
        )

        await self.log(event.emoji.guild, LogType.EMOJI_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_emoji_delete(self, event):
        parts = moderator_info(event)
        parts.append(f'Emoji URL: <{event.emoji.url}>')

        msg = f'\N{WASTEBASKET}{VS16} `{describe_emoji(event.emoji)}` was deleted{join_parts(parts)}'
        await self.log(event.emoji.guild, LogType.EMOJI_DELETE, msg)

    @Plugin.listener()
    async def on_mouse_channel_create(self, event):
        parts = moderator_info(event)
        msg = f'\N{PAGE FACING UP} `#{describe(event.channel)}` created{join_parts(parts)}'

        await self.log(event.channel.guild, LogType.CHANNEL_CREATE, msg)

    @Plugin.listener()
    async def on_mouse_channel_name_update(self, event):
        parts = moderator_info(event)

        msg = (
            f'\N{PAPERCLIP} `#{describe(event.channel)}` was renamed from '
            f'`{code_safe(event.before)}` to `{code_safe(event.after)}`{join_parts(parts)}'
        )

        await self.log(event.channel.guild, LogType.CHANNEL_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_channel_slowmode_delay_update(self, event):
        parts = moderator_info(event)

        msg = (
            f'\N{PAPERCLIP} `#{describe(event.channel)}` slowmode changed from '
            f'`{human_delta(event.before)}` to `{human_delta(event.after)}`{join_parts(parts)}'
        )

        await self.log(event.channel.guild, LogType.CHANNEL_UPDATE, msg)

    @Plugin.listener()
    async def on_mouse_channel_delete(self, event):
        parts = moderator_info(event)
        msg = f'\N{WASTEBASKET} `#{describe(event.channel)}` deleted{join_parts(parts)}'

        await self.log(event.channel.guild, LogType.CHANNEL_DELETE, msg)

    @Plugin.listener()
    async def on_mouse_message_edit(self, event):
        ...  # TODO

    @Plugin.listener()
    async def on_mouse_message_delete(self, event):
        if event.message.author.bot:
            return

        parts = moderator_info(event)

        if event.message.content:
            content = escape_formatting(event.message.content)
            parts.append(f'Content: {indent_multiline(content)}')

        if event.message.embeds:
            data = [x.to_dict() for x in event.message.embeds]
            data = json.dumps(data, indent=2, sort_keys=True)

            text = f'// Note that this data will expire!\n\n{data}\n'
            paste_url = await create_paste(self.mousey.session, text)

            parts.append(f'Embed Data: <{paste_url}>')  # This isn't very pretty, but okay for now

        if event.message.attachments:
            urls = '\n'.join(f'<{x.proxy_url}>' for x in event.message.attachments)
            parts.append(f'Attachments: {indent_multiline(urls)}')

        msg = (
            f'\N{PUT LITTER IN ITS PLACE SYMBOL} '
            f'`{describe_user(event.message.author)}` message `{event.message.id}` '
            f'deleted in `{event.message.channel}` {event.message.author.mention}{join_parts(parts)}'
        )

        await self.log(event.message.guild, LogType.MESSAGE_DELETE, msg, target=event.message.author)

    @Plugin.listener()
    async def on_mouse_bulk_message_delete(self, event):
        parts = moderator_info(event)

        if event.archive_url is not None:
            parts.append(f'Archive: <{event.archive_url}>')
        else:
            parts.append(f'Archive: Temporarily unable to create archive')

        users = collections.Counter()

        for message in event.messages:
            users[message.author] += 1

        def fmt_author(data):
            author, count = data
            return f'`{describe_user(author)}` ({count})'

        total = len(users)

        names = ', '.join(map(fmt_author, users.most_common(3)))
        extra = ', \N{HORIZONTAL ELLIPSIS}' if total > 3 else ''

        parts.append(f'{Plural(total):Author}: {names}{extra}')  # Includes IDs for searching

        msg = (
            f'\N{PUT LITTER IN ITS PLACE SYMBOL} '
            f'{len(event.messages)} messages deleted in `#{event.messages[0].channel}`{join_parts(parts)}'
        )

        await self.log(event.messages[0].guild, LogType.MESSAGE_BULK_DELETE, msg)
