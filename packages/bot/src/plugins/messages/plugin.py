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
import itertools

import aiohttp
import discord
import more_itertools
from discord.ext import tasks

from ... import BulkMessageDeleteEvent, HTTPException, MessageDeleteEvent, MessageEditEvent, Plugin
from ...utils import PGSQL_ARG_LIMIT, multirow_insert, serialize_user
from .crypto import decrypt, decrypt_json, encrypt, encrypt_json
from .errors import InvalidMessage
from .message import Message
from .utils import attachment_paths, serialize_datetime


def encrypt_message(message):
    """Prepare for a message to be stored."""

    data = [
        # Order of fields in INSERT query
        message['id'],
        message['author_id'],
        message['channel_id'],
        encrypt(message['content']),
        list(map(encrypt_json, message['embeds'])),
        list(map(encrypt, message['attachments'])),
        message['edited_at'],
        message['deleted_at'],
    ]

    return data


def decrypt_message(data):
    """Decrypt a message fetched from the database."""

    message = {
        'id': data['id'],
        'author_id': data['author_id'],
        'channel_id': data['channel_id'],
        'content': decrypt(data['content']),
        'embeds': list(map(decrypt_json, data['embeds'])),
        'attachments': list(map(decrypt, data['attachments'])),
        'edited_at': data['edited_at'],
        'deleted_at': data['deleted_at'],
    }

    return message


class Messages(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self._messages = {}
        self._updating = {}

        self.persist_messages.start()
        self.delete_old_messages.start()

    def cog_unload(self):
        self.persist_messages.stop()
        self.delete_old_messages.stop()

    async def get_message(self, message_id):
        data = await self._get_message(message_id)

        if data is not None:
            return await self._create_message(data)

    async def get_messages(self, channel, before=None, limit=100):
        if before is None:
            now = discord.utils.utcnow()
            before = discord.utils.time_snowflake(now)
        elif isinstance(before, datetime.datetime):
            before = discord.utils.time_snowflake(before)

        async with self.mousey.db.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT id, author_id, channel_id, content, embeds, attachments, edited_at, deleted_at
                FROM messages
                WHERE channel_id = $1 AND id < $2
                ORDER BY id DESC
                LIMIT $3
                """,
                channel.id,
                before,
                limit,
            )

        messages = map(decrypt_message, records)
        return [await self._create_message(x) for x in messages]

    async def create_archive(self, messages):
        archived = []
        guild_id = messages[0].guild.id

        for message in messages:
            archived.append(
                {
                    'id': message.id,
                    'author': serialize_user(message.author),
                    'channel': {
                        'id': message.channel.id,  # Other fields are discarded,,
                    },
                    'content': message.content,
                    'mentions': list(map(serialize_user, message.user_mentions)),
                    'embeds': [x.to_dict() for x in message.embeds],
                    'attachments': attachment_paths(message.attachments),
                    'edited_at': serialize_datetime(message.edited_at),
                    'deleted_at': serialize_datetime(message.deleted_at),
                }
            )

        try:
            data = await self.mousey.api.create_archive(guild_id, archived)
        except (asyncio.TimeoutError, aiohttp.ClientError, HTTPException):
            return

        return 'https://dash.mousey.app/archives/' + str(data['id'])  # No local URLs for now

    @Plugin.listener()
    async def on_message(self, message):
        author_id = None if message.webhook_id else message.author.id

        embeds = list(x.to_dict() for x in message.embeds)
        attachments = attachment_paths(message.attachments)

        await self._update_message(
            dict(
                id=message.id,
                author_id=author_id,
                channel_id=message.channel.id,
                content=message.system_content or '',
                embeds=embeds,
                attachments=attachments,
                edited_at=None,
                deleted_at=None,
            )
        )

        if message.webhook_id is not None:
            await self._set_author(message.id, message.author)

    @Plugin.listener()
    async def on_raw_message_edit(self, payload):
        message_id = payload.message_id
        message = await self._get_message(message_id)

        if message is None:
            return

        updates = {}

        def find_field(name, transform=lambda x: x, key=None):
            value = payload.data.get(name)

            if value is not None:
                updates[key or name] = transform(value)

        fields = (
            ('content',),
            ('embeds',),
            ('edited_timestamp', discord.utils.parse_time, 'edited_at'),
        )

        for args in fields:
            find_field(*args)

        if not updates:
            return

        old = await self._create_message(message)
        message = await self._update_message(message, **updates)

        self.mousey.dispatch('mouse_message_edit', MessageEditEvent(old, await self._create_message(message)))

    @Plugin.listener()
    async def on_raw_message_delete(self, payload):
        message_id = payload.message_id
        message = await self._get_message(message_id)

        if message is None:
            return

        now = discord.utils.utcnow()
        message = await self._update_message(message, deleted_at=now)

        self.mousey.dispatch('mouse_message_delete', MessageDeleteEvent(await self._create_message(message)))

    @Plugin.listener()
    async def on_raw_bulk_message_delete(self, payload):
        messages = []
        now = discord.utils.utcnow()

        for message_id in sorted(payload.message_ids):
            message = await self._get_message(message_id)

            if message is None:
                continue

            message = await self._update_message(message, deleted_at=now)
            messages.append(await self._create_message(message))

        if not messages:
            return

        archive_url = await self.create_archive(messages)
        self.mousey.dispatch('mouse_bulk_message_delete', BulkMessageDeleteEvent(messages, archive_url))

    async def _get_message(self, message_id):
        try:
            return self._messages.get(message_id) or self._updating[message_id]
        except KeyError:
            pass

        async with self.mousey.db.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT id, author_id, channel_id, content, embeds, attachments, edited_at, deleted_at
                FROM messages
                WHERE id = $1
                """,
                message_id,
            )

        if record is not None:
            return decrypt_message(record)

    async def _update_message(self, message, **fields):
        # Don't update the original reference
        message = {**message, **fields}

        message_id = message['id']
        self._messages[message_id] = message

        return message

    async def _create_message(self, message):
        channel_id = message['channel_id']
        channel = self.mousey.get_channel(channel_id)

        if channel is None:
            raise InvalidMessage

        author = await self._get_author(message, channel.guild)
        return Message(**message, author=author, channel=channel)

    async def _set_author(self, message_id, author):
        data = {
            'id': author.id,
            'bot': author.bot,
            'username': author.name,
            'discriminator': author.discriminator,
            'avatar': author.avatar and author.avatar.key,
        }

        data = encrypt_json(data)
        await self.mousey.redis.set(f'mousey:message-author:{message_id}', data, ex=86400 * 30)

    async def _get_author(self, message, guild):
        message_id = message['id']
        author_id = message['author_id']

        if author_id is None:  # Webhook user
            data = await self.mousey.redis.get(f'mousey:message-author:{message_id}')

            if data is None:
                raise InvalidMessage

            # noinspection PyProtectedMember
            return discord.User(data=decrypt_json(data), state=self.mousey._connection)

        return guild.get_member(author_id) or self.mousey.get_user(author_id) or await self.mousey.fetch_user(author_id)

    # Background tasks

    @tasks.loop(seconds=1)
    async def persist_messages(self):
        await self._persist_messages()

    @persist_messages.after_loop
    async def _persist_messages(self):
        self._updating = self._messages
        self._messages = {}

        max_size = int(PGSQL_ARG_LIMIT / 8)
        updates = map(encrypt_message, self._updating.values())

        async with self.mousey.db.acquire() as conn:
            for chunk in more_itertools.chunked(updates, max_size):
                await conn.execute(
                    f"""
                    INSERT INTO messages (
                      id, author_id, channel_id, content, embeds, attachments, edited_at, deleted_at
                    )
                    VALUES {multirow_insert(chunk)}
                    ON CONFLICT (id) DO UPDATE
                    SET content = EXCLUDED.content,
                        embeds = EXCLUDED.embeds, attachments = EXCLUDED.attachments,
                        edited_at = EXCLUDED.edited_at, deleted_at = EXCLUDED.deleted_at
                    """,
                    *itertools.chain.from_iterable(chunk),
                )

    @tasks.loop(hours=1)
    async def delete_old_messages(self):
        now = discord.utils.utcnow()

        month_ago = now - datetime.timedelta(days=30)
        snowflake = discord.utils.time_snowflake(month_ago)

        async with self.mousey.db.acquire() as conn:
            await conn.execute('DELETE FROM messages WHERE id < $1', snowflake)
