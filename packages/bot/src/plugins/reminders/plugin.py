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
import datetime
import re
import typing

import discord
from discord.ext import commands

from ... import PURRL, NotFound, Plugin, bot_has_permissions, command, group
from ...utils import (
    PaginatorInterface,
    Plural,
    TimeConverter,
    close_interface_context,
    create_task,
    human_delta,
    serialize_user,
)
from .converter import reminder_content, reminder_id


def is_mentionable(role):
    return role.mentionable


class Reminders(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self._next = None
        self._task = create_task(self._fulfill_reminders())

    def cog_unload(self):
        if not self._task.done():
            self._task.cancel()

    @group(aliases=['reminder', 'remindme'])
    @bot_has_permissions(send_messages=True)
    async def remind(self, ctx, time: TimeConverter, *, message: reminder_content = None):
        """
        Create a reminder at the specified time.

        Reply to a message to be reminded about it instead of the invocation message.

        Time can be given as a duration or ISO8601 date with up to minute precision.
        Message can be any string up to 500 characters or will default to being empty.
          Note: You may mention roles or @everyone if you have required permissions.

        Example: `{prefix}remind 2 days 16 hr Ask for Nelly's phone number!`
        Example: `{prefix}remind 2021-1-1 8:00 How is the new year, Mousey?`
        \u200b
        """
        # TODO: Support other date formats

        if isinstance(time, datetime.timedelta):
            expires = datetime.datetime.utcnow() + time
            response = f'in {human_delta(time)}'
        else:  # datetime.datetime
            expires = time
            response = 'at ' + time.strftime('%Y-%m-%d %H:%M')

        data = {
            'user': serialize_user(ctx.author),
            'guild_id': ctx.guild.id,
            'channel_id': getattr(ctx.channel, 'parent_id', ctx.channel.id),
            'message_id': ctx.message.id,
            'expires_at': expires.isoformat(),
            'message': message or 'something',
        }

        if isinstance(ctx.channel, discord.Thread):
            data['thread_id'] = ctx.channel.id

        if ctx.message.reference is not None:
            data['referenced_message_id'] = ctx.message.reference.message_id

        resp = await self.mousey.api.create_reminder(data)
        idx = resp['id']

        if self._next is None or self._next > expires:
            self._task.cancel()
            self._task = create_task(self._fulfill_reminders())

        about = f'about {message} ' if message else ''
        await ctx.send(f'I will remind you {about}{response}. #{idx}')

    @remind.command('edit')
    @bot_has_permissions(send_messages=True)
    async def remind_edit(
        self, ctx, reminder: reminder_id, time: typing.Optional[TimeConverter], *, message: reminder_content = None
    ):
        """
        Edit one of your own reminders.

        Reminder must be specified using its ID.
          Note: Reminder IDs are visible on reminder create and using `{prefix}remind list`.
        Time can be given as a duration or ISO8601 date with up to minute precision.
        Message can be any string up to 500 characters.
          Note: You may mention roles or @everyone if you have required permissions.

        Example: `{prefix}remind edit 147 6h`
        Example: `{prefix}remind edit 147 Message Nelly and Mousey`
        """

        if time is None and message is None:
            await ctx.send('Unable to edit reminder, please specify a time or message.')
            return

        try:
            resp = await self.mousey.api.get_reminder(reminder)
        except NotFound:
            await ctx.send('Unable to edit reminder, it may be deleted or not belong to you.')
            return

        if resp['user_id'] != ctx.author.id:
            await ctx.send('Unable to edit reminder, it may be deleted or not belong to you.')
            return

        data = {}

        if time is not None:
            if isinstance(time, datetime.timedelta):
                time = datetime.datetime.utcnow() + time

            data['expires_at'] = time.isoformat()

        if message is not None:
            data['message'] = message

        try:
            resp = await self.mousey.api.update_reminder(reminder, data)
        except NotFound:
            await ctx.send('Unable to update reminder, it may have already expired before being edited.')
            return

        now = datetime.datetime.utcnow()
        expires_at = datetime.datetime.fromisoformat(resp['expires_at'])

        if self._next is not None:
            self._task.cancel()
            self._task = create_task(self._fulfill_reminders())

        await ctx.send(
            f'Successfully updated reminder #{reminder}, I will remind you in {human_delta(expires_at - now)}.'
        )

    @remind.command('list')
    @bot_has_permissions(add_reactions=True, send_messages=True)
    async def remind_list(self, ctx):
        """
        View all of your upcoming reminders in the current server.

        Example: `{prefix}remind list`
        """

        try:
            resp = await self.mousey.api.get_member_reminders(ctx.guild.id, ctx.author.id)
        except NotFound:
            await ctx.send('You have no upcoming reminders!')
        else:
            prefix = self.mousey.get_cog('Help').clean_prefix(ctx.prefix)
            usage = f'{self.remind_cancel.qualified_name} {self.remind_cancel.signature}'

            paginator = commands.Paginator(
                max_size=1000,
                prefix='Your upcoming reminders:\n',
                suffix=f'\nCancel reminders using `{prefix}{usage}`',
            )

            now = datetime.datetime.utcnow()

            for index, data in enumerate(resp, 1):
                idx = data['id']
                message = data['message']

                expires_at = datetime.datetime.fromisoformat(data['expires_at'])
                expires_at = human_delta(expires_at - now)

                paginator.add_line(f'**#{idx}** in `{expires_at}`:\n{message}')

                if not index % 10:  # Display a max of 10 results per page
                    paginator.close_page()

            interface = PaginatorInterface(self.mousey, paginator, owner=ctx.author, timeout=600)

            await interface.send_to(ctx.channel)
            close_interface_context(ctx, interface)

    @command(hidden=True, help=remind_list.help)
    @bot_has_permissions(send_messages=True)
    async def reminders(self, ctx):
        await ctx.invoke(self.remind_list)

    @remind.command('cancel', aliases=['delete'])
    @bot_has_permissions(send_messages=True)
    async def remind_cancel(self, ctx, reminders: commands.Greedy[reminder_id]):
        """
        Cancel one or more of your own reminders.

        Reminders must be specified using their IDs.
          Note: Reminder IDs are visible on reminder create and using `{prefix}remind list`.

        Example: `{prefix}remind cancel 147`
        """

        deleted = 0

        for idx in reminders:
            try:
                resp = await self.mousey.api.get_reminder(idx)
            except NotFound:
                continue

            if resp['user_id'] != ctx.author.id:
                continue

            try:
                await self.mousey.api.delete_reminder(idx)
            except NotFound:
                pass
            else:
                deleted += 1

        if deleted:
            if self._next is not None:
                self._task.cancel()
                self._task = create_task(self._fulfill_reminders())

            msg = f'Successfully deleted {Plural(deleted):reminder}.'
        else:
            msg = 'Unable to delete reminder, it may already be deleted or not belong to you.'

        await ctx.send(msg)

    async def _fulfill_reminders(self):
        await self.mousey.wait_until_ready()

        while not self.mousey.is_closed():
            try:
                resp = await self.mousey.api.get_reminders(self.mousey.shard_id)
            except NotFound:
                return

            reminder = resp[0]
            expires_at = datetime.datetime.fromisoformat(reminder['expires_at'])

            self._next = expires_at
            await discord.utils.sleep_until(expires_at)

            guild = self.mousey.get_guild(reminder['guild_id'])

            if guild is None:
                await asyncio.shield(self._delete_reminder(reminder['id']))
                continue

            if guild.unavailable:
                # Reschedule until the guild is hopefully available again
                expires_at += datetime.timedelta(minutes=5)
                await asyncio.shield(self._reschedule_reminder(reminder['id'], expires_at))
                continue

            channel = guild.get_channel(reminder['channel_id'])

            if channel is None or not channel.permissions_for(channel.guild.me).send_messages:
                await asyncio.shield(self._delete_reminder(reminder['id']))
                continue

            message_id = reminder['message_id']

            now = discord.utils.utcnow()
            created_at = discord.utils.snowflake_time(message_id)

            user_id = reminder['user_id']
            content = reminder['message']
            created = human_delta(now - created_at)

            content = f'Hey <@!{user_id}> {PURRL}! You asked to be reminded about {content} {created} ago.'

            member = guild.get_member(user_id)

            roles = re.findall(r'<@&?(\d{15,21})>', reminder['message'])
            roles = filter(None, (guild.get_role(int(x)) for x in roles))

            if member is None:
                everyone = False
                roles = list(filter(is_mentionable, roles))
            else:
                everyone = channel.permissions_for(member).mention_everyone
                roles = [x for x in roles if everyone or is_mentionable(x)]

            destination_id = reminder['thread_id'] or channel.id

            referenced_message_id = reminder['referenced_message_id'] or message_id
            mentions = discord.AllowedMentions(everyone=everyone, roles=set(roles), users=True)

            message_reference = {
                'fail_if_not_exists': False,
                'message_id': referenced_message_id,
            }

            try:
                # Use http.send_message in case this reminder is for an archived or deleted thread
                # If the thread is deleted we get a 404 error either way, so we can just not do the request
                await self.mousey.http.send_message(
                    destination_id, content, allowed_mentions=mentions.to_dict(), message_reference=message_reference
                )
            except discord.HTTPException as e:
                pass

            await asyncio.shield(self._delete_reminder(reminder['id']))

    async def _delete_reminder(self, idx):
        self._next = None

        try:
            await self.mousey.api.delete_reminder(idx)
        except NotFound:
            pass

    async def _reschedule_reminder(self, idx, expires_at):
        self._next = None
        expires_at = expires_at.isoformat()

        try:
            await self.mousey.api.update_reminder(idx, expires_at)
        except NotFound:
            pass
