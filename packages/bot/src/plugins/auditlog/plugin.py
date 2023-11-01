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

from __future__ import annotations

import asyncio
import collections
import datetime
import re
from typing import Optional, Union

import aiohttp
import discord

from ... import Mousey, Plugin
from ...utils import create_task
from .lookup import CheckFunction, Lookup


FETCH_INTERVAL = 2


class AuditLog(Plugin):
    """
    Periodically fetches audit log entries from the API if needed.

    Instead of fetching on a per-event basis we queue lookups per guild to allow
    another bot to eg. execute 50 bans without us looking up 50 entries individually.

    Note that most of the time this functionality will not actually be useful,
    however it should still provide a nice(r) interface to fetch a specific entry.
    """

    def __init__(self, mousey: Mousey):
        super().__init__(mousey)

        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._lookups: collections.defaultdict[int, set[Lookup]] = collections.defaultdict(set)

    def cog_unload(self) -> None:
        for task in self._tasks.values():
            task.cancel()

    async def fetch_entry(
        self,
        guild: discord.Guild,
        action: discord.AuditLogAction,
        *,
        target: Optional[discord.abc.Snowflake] = None,
        check: Optional[CheckFunction] = None,
        timeout: float = 8,
    ) -> Union[discord.AuditLogEntry, None]:
        lookup = Lookup(action, target, check, timeout)

        if not guild.me.guild_permissions.view_audit_log:
            lookup.set_result(None)
        else:
            self._queue(guild.id, lookup)

        return await lookup.wait()

    def cancel_guild_task(self, guild_id: int) -> None:
        try:
            del self._lookups[guild_id]
        except KeyError:
            pass

        try:
            self._tasks.pop(guild_id).cancel()
        except KeyError:
            pass

    def _queue(self, guild_id: int, lookup: Lookup) -> None:
        task = self._tasks.get(guild_id)
        self._lookups[guild_id].add(lookup)

        if task is None or task.done():
            self._tasks[guild_id] = create_task(self._do_lookups(guild_id))

    async def _do_lookups(self, guild_id: int) -> None:
        while self._lookups[guild_id]:
            await asyncio.sleep(FETCH_INTERVAL)
            self._remove_expired_entries(guild_id)

            if self._lookups[guild_id]:
                await self._perform_lookup(guild_id)

    async def _perform_lookup(self, guild_id: int) -> None:
        guild = self.mousey.get_guild(guild_id)

        if guild is None:
            return

        entries: list[discord.AuditLogEntry] = []

        now = discord.utils.utcnow()
        start = now - datetime.timedelta(seconds=16)

        try:
            async for entry in guild.audit_logs(limit=None):
                if entry.created_at < start:
                    break

                entries.append(entry)
        except (asyncio.TimeoutError, aiohttp.ClientError, discord.HTTPException):
            return

        # Resolve Lookups in chronological event order if possible
        for entry in reversed(entries):
            await self._check_entry(guild_id, entry)

    async def _check_entry(self, guild_id: int, entry: discord.AuditLogEntry) -> None:
        for lookup in tuple(self._lookups[guild_id]):
            if not lookup.matches(entry):
                continue

            self._augment_entry(entry)

            lookup.set_result(entry)
            self._lookups[guild_id].remove(lookup)

            await asyncio.sleep(0)  # Yield to wake up Futures in order, hopefully

    def _augment_entry(self, entry: discord.AuditLogEntry) -> None:
        if entry.user is None or entry.reason is None or not entry.user.bot:
            return

        # Match other bots' audit log patterns:
        # lostluma 69198249432449024 reason
        # lostluma (69198249432449024) reason
        # lostluma (ID: 69198249432449024): reason
        # By lostluma (ID 69198249432449024): reason
        # This works for R. Danny and PythonistaBot, maybe there are other commonly used ones as well.
        match = re.match(r'(?:Action Done By|By)?\s?(?P<username>[\w\.]{2,32}|.{2,32}#\d{4})\s?(\()?(?:ID:?)?\s?(?P<id>\d{15,21})(?(2)\)|):?(?P<reason>.+)?', entry.reason, re.I)

        if match is None:
            return

        user_id = match.group('id')
        user = entry.guild.get_member(int(user_id))

        if user is None:
            return

        entry.user = user

        if match.group('reason') is None:
            entry.reason = None
        else:
            entry.reason = match.group('reason').strip()

    def _remove_expired_entries(self, guild_id: int) -> None:
        active: set[Lookup] = set()
        lookups = self._lookups[guild_id]

        for lookup in lookups:
            if not lookup.is_expired():
                active.add(lookup)
            else:
                lookup.set_result(None)

        self._lookups[guild_id] = active

    @Plugin.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        self.cancel_guild_task(guild.id)
