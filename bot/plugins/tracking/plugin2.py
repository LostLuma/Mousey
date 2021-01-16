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

import datetime
import itertools
import time
import typing

import aredis
import discord
import more_itertools
from discord.ext import tasks

from ... import Plugin


def current_time():
    return int(time.time())


def maybe_datetime(value):
    if value:
        return datetime.datetime.utcfromtimestamp(int(value))


def not_bot(func):
    def wrapper(self, member):
        if not member.bot:
            return func(self, member)

    return wrapper


class LastMemberStatus(typing.NamedTuple):
    status: datetime.datetime = None

    seen: datetime.datetime = None
    spoke: datetime.datetime = None


class Tracking(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self._updates = {}

        self.persist_updates.start()
        self.persist_updates.add_exception_type(aredis.BusyLoadingError)

    def cog_unload(self):
        self.persist_updates.stop()

    async def get_last_status(self, member):
        members = [member]
        return (await self.bulk_last_status(members))[0]

    async def bulk_last_status(self, members):
        keys = itertools.chain.from_iterable(
            (
                f'mousey:last-status:{member.id}',
                f'mousey:last-seen:{member.guild.id}-{member.id}',
                f'mousey:last-spoke:{member.guild.id}-{member.id}',
            )
            for member in members
        )

        results = await self.mousey.redis.mget(keys)
        return [LastMemberStatus(*map(maybe_datetime, x)) for x in more_itertools.chunked(results, 3)]

    async def get_removed_at(self, member):
        key = f'mousey:removed-at:{member.guild.id}-{member.id}'
        return maybe_datetime(await self.mousey.redis.get(key))

    @Plugin.listener()
    async def on_member_join(self, member):
        self._update_last_seen(member)

    @Plugin.listener()
    async def on_typing(self, channel, member, when):
        self._update_last_seen(member)

    @Plugin.listener()
    async def on_message(self, message):
        if message.type != discord.MessageType.new_member:
            self._update_last_spoke(message.author)

    @Plugin.listener()
    async def on_mouse_message_edit(self, before, after):
        if before.content != after.content:
            self._update_last_spoke(before.author)

    @Plugin.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.mousey.get_guild(payload.guild_id)
        self._update_last_seen(guild.get_member(payload.user_id))

    @Plugin.listener()
    async def on_member_update(self, before, after):
        if before.status != after.status:
            self._update_last_status(before)

    @Plugin.listener()
    async def on_mouse_nick_change(self, member, before, after, moderator, reason):
        if moderator is not None:
            self._update_last_seen(moderator)

    @Plugin.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel:
            self._update_last_seen(member)

    @Plugin.listener()
    async def on_member_remove(self, member):
        self._set_removed_at(member)

        keys = [
            f'mousey:last-seen:{member.guild.id}-{member.id}',
            f'mousey:last-spoke:{member.guild.id}-{member.id}',
        ]

        await self.mousey.redis.delete(*keys)

    @Plugin.listener()
    async def on_mouse_guild_remove(self, guild):
        keys = itertools.chain.from_iterable(
            (
                f'mousey:last-seen:{member.guild.id}-{member.id}',
                f'mousey:last-spoke:{member.guild.id}-{member.id}',
            )
            for member in guild.members
        )

        await self.mousey.redis.delete(*keys)

    @not_bot
    def _update_last_status(self, member):
        now = current_time()
        self._updates[f'mousey:last-status:{member.id}'] = now

    @not_bot
    def _update_last_seen(self, member):
        now = current_time()
        self._updates[f'mousey:last-seen:{member.guild.id}-{member.id}'] = now

    @not_bot
    def _update_last_spoke(self, member):
        now = current_time()

        self._updates[f'mousey:last-seen:{member.guild.id}-{member.id}'] = now
        self._updates[f'mousey:last-spoke:{member.guild.id}-{member.id}'] = now

    @not_bot
    def _set_removed_at(self, member):
        now = current_time()
        self._updates[f'mousey:removed-at:{member.guild.id}-{member.id}'] = now

    @tasks.loop(seconds=1)
    async def persist_updates(self):
        await self._persist_updates()

    @persist_updates.after_loop
    async def _persist_updates(self):
        updates = self._updates

        if not updates:
            return

        self._updates = dict()
        await self.mousey.redis.mset(updates)
