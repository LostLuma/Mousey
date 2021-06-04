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
import time
import typing

import discord
import more_itertools
from discord.ext import tasks

from ... import Plugin
from ...utils import PGSQL_ARG_LIMIT, multirow_insert


def not_bot(func):
    # fmt: off
    if not asyncio.iscoroutinefunction(func):
        def wrapper(self, member):
            if not member.bot:
                return func(self, member)
    else:
        async def wrapper(self, member):
            if not member.bot:
                return await func(self, member)
    # fmt: on

    return wrapper


class LastMemberStatus(typing.NamedTuple):
    status: datetime.datetime = None

    seen: datetime.datetime = None
    spoke: datetime.datetime = None


class Tracking(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        # Discord status updates
        self._status_updates = {}

        # Any activity in guild
        self._seen_updates = {}
        # Sent message in guild
        self._spoke_updates = {}

        self.persist_updates.start()

    def cog_unload(self):
        self.persist_updates.stop()

    async def get_last_status(self, member):
        statuses = await self.bulk_last_status(member)
        return statuses[0]

    async def bulk_last_status(self, *members):
        guild_id = members[0].guild.id
        user_ids = [x.id for x in members]

        async with self.mousey.db.acquire() as conn:
            status_records = await conn.fetch(
                'SELECT user_id, updated_at FROM status_updates WHERE user_id = ANY($1)', user_ids
            )

            seen_records = await conn.fetch(
                'SELECT user_id, updated_at FROM seen_updates WHERE guild_id = $1 AND user_id = ANY($2)',
                guild_id,
                user_ids,
            )

            spoke_records = await conn.fetch(
                'SELECT user_id, updated_at FROM spoke_updates WHERE guild_id = $1 AND user_id = ANY($2)',
                guild_id,
                user_ids,
            )

        status_updates = {x['user_id']: x['updated_at'] for x in status_records}
        seen_updates = {x['user_id']: x['updated_at'] for x in seen_records}
        spoke_updates = {x['user_id']: x['updated_at'] for x in spoke_records}

        return [LastMemberStatus(status_updates.get(x), seen_updates.get(x), spoke_updates.get(x)) for x in user_ids]

    async def get_removed_at(self, member):
        value = await self.mousey.redis.get(f'mousey:removed-at:{member.guild.id}-{member.id}')

        if value is not None:
            return datetime.datetime.utcfromtimestamp(int(value))

    @Plugin.listener()
    async def on_member_join(self, member):
        self._update_last_seen(member)

    @Plugin.listener()
    async def on_typing(self, channel, member, when):
        self._update_last_seen(member)

    @Plugin.listener()
    async def on_message(self, message):
        if message.type is not discord.MessageType.new_member:
            self._update_last_spoke(message.author)

    @Plugin.listener()
    async def on_mouse_message_edit(self, event):
        if event.before.content != event.after.content:
            self._update_last_spoke(event.after.author)

    @Plugin.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.mousey.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)

        if member is not None:
            self._update_last_seen(member)

    @Plugin.listener()
    async def on_member_update(self, before, after):
        if before.status is not after.status:
            self._update_last_status(before)

    @Plugin.listener()
    async def on_mouse_nick_change(self, event):
        if event.moderator is not None:
            self._update_last_seen(event.moderator)

    @Plugin.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel:
            self._update_last_seen(member)

    @Plugin.listener()
    async def on_member_remove(self, member):
        await self._set_removed_at(member)
        await self._remove_member_data(member)

    @Plugin.listener()
    async def on_mouse_guild_remove(self, event):
        await self._remove_guild_member_data(event.guild)

    @not_bot
    def _update_last_status(self, member):
        now = datetime.datetime.utcnow()
        self._status_updates[member.id] = now

    @not_bot
    def _update_last_seen(self, member):
        now = datetime.datetime.utcnow()
        self._seen_updates[member.guild.id, member.id] = now

    @not_bot
    def _update_last_spoke(self, member):
        now = datetime.datetime.utcnow()

        self._seen_updates[member.guild.id, member.id] = now
        self._spoke_updates[member.guild.id, member.id] = now

    @not_bot
    async def _set_removed_at(self, member):
        now = int(time.time())
        await self.mousey.redis.set(f'mousey:removed-at:{member.guild.id}-{member.id}', now, ex=86400 * 180)

    @not_bot
    async def _remove_member_data(self, member):
        async with self.mousey.db.acquire() as conn:
            await conn.execute(
                'DELETE FROM seen_updates WHERE guild_id = $1 AND user_id = $2', member.guild.id, member.id
            )

            await conn.execute(
                'DELETE FROM spoke_updates WHERE guild_id = $1 AND user_id = $2', member.guild.id, member.id
            )

    async def _remove_guild_member_data(self, guild):
        async with self.mousey.db.acquire() as conn:
            await conn.execute('DELETE FROM seen_updates WHERE guild_id = $1', guild.id)
            await conn.execute('DELETE FROM spoke_updates WHERE guild_id = $1', guild.id)

    @tasks.loop(seconds=1)
    async def persist_updates(self):
        await self._persist_updates()

    @persist_updates.after_loop
    async def _persist_updates(self):
        await self._persist_status_updates()

        updates, self._seen_updates = self._seen_updates, {}
        await self._persist_guild_updates('seen_updates', updates)

        updates, self._spoke_updates = self._spoke_updates, {}
        await self._persist_guild_updates('spoke_updates', updates)

    async def _persist_status_updates(self):
        updates, self._status_updates = self._status_updates, {}

        if not updates:
            return

        max_size = int(PGSQL_ARG_LIMIT / 2)
        updates = sorted(updates.items())  # Sort prevents deadlock

        async with self.mousey.db.acquire() as conn:
            for chunk in more_itertools.chunked(updates, max_size):
                await conn.execute(
                    f"""
                    INSERT INTO status_updates (user_id, updated_at)
                    VALUES {multirow_insert(chunk)}
                    ON CONFLICT (user_id) DO UPDATE
                    SET updated_at = EXCLUDED.updated_at
                    """,
                    *itertools.chain.from_iterable(chunk),
                )

    async def _persist_guild_updates(self, table, updates):
        if not updates:
            return

        max_size = int(PGSQL_ARG_LIMIT / 3)
        # guild_user_id is a tuple of guild id, user id
        updates = [(*guild_user_id, seen) for guild_user_id, seen in updates.items()]

        async with self.mousey.db.acquire() as conn:
            for chunk in more_itertools.chunked(updates, max_size):
                await conn.execute(
                    f"""
                    INSERT INTO {table} (guild_id, user_id, updated_at)
                    VALUES {multirow_insert(chunk)}
                    ON CONFLICT (guild_id, user_id) DO UPDATE
                    SET updated_at = EXCLUDED.updated_at
                    """,
                    *itertools.chain.from_iterable(chunk),
                )
