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
import datetime
import logging

import aiohttp
import discord

from ... import Plugin
from ...utils import create_task
from .lookup import Lookup


log = logging.getLogger(__name__)


class AuditLog(Plugin):
    """
    Periodically fetches audit log entries from the API if needed.

    Instead of fetching on a per-event basis we queue lookups per guild to allow
    another bot to eg. execute 50 bans without us looking up 50 entries individually.

    Note that most of the time this functionality will not actually be useful,
    however it should still provide a nice(r) interface to fetch a specific entry.
    """

    def __init__(self, mousey):
        super().__init__(mousey)

        self._tasks = {}
        self._pending = collections.defaultdict(set)

    def cog_unload(self):
        for task in self._tasks.values():
            task.cancel()

        for lookups in self._pending.values():
            for lookup in lookups:
                lookup.set_result(None)

    def get_entry(self, guild, action, *, target=None, check=None, timeout=8):
        lookup = Lookup(action, target, check, timeout)

        if guild.me.guild_permissions.view_audit_log:
            self._queue(guild.id, lookup)
        else:
            lookup.set_result(None)  # :ablobsadrain:

        return lookup.wait()

    def _queue(self, guild_id, lookup):
        task = self._tasks.get(guild_id)
        self._pending[guild_id].add(lookup)

        if task is None or task.done():
            self._tasks[guild_id] = create_task(self._do_lookups(guild_id))

    async def _do_lookups(self, guild_id):
        while self._pending[guild_id]:
            await asyncio.sleep(2)

            for lookup in tuple(self._pending[guild_id]):
                if lookup.expired:
                    lookup.set_result(None)
                    self._pending[guild_id].discard(lookup)

            await self._perform_lookup(guild_id)

    async def _perform_lookup(self, guild_id):
        now = discord.utils.utcnow()
        start = now - datetime.timedelta(seconds=16)

        entries = []

        guild = self.mousey.get_guild(guild_id)

        # Fetch all recent entries instead of a count
        # This should never really request more than 100
        try:
            async for entry in guild.audit_logs(limit=None):
                if entry.created_at < start:
                    break

                entries.append(entry)
        except (asyncio.TimeoutError, aiohttp.ClientError, discord.HTTPException):
            return

        # If this happens too often I might need to rethink this
        if len(entries) >= 100:
            log.info(f'Fetched {len(entries)} (> 100) audit log entries in {guild!r}.')

        # Resolve Lookups in chronological event order if possible
        for entry in reversed(entries):
            await self._check_entry(guild_id, entry)

    async def _check_entry(self, guild_id, entry):
        for lookup in tuple(self._pending[guild_id]):
            if not lookup.matches(entry):
                continue

            # Remove trailing newlines etc.
            # For all code handling reasons
            if entry.reason is not None:
                entry.reason = entry.reason.strip()

            lookup.set_result(entry)
            self._pending[guild_id].discard(lookup)

            await asyncio.sleep(0)  # Yield to hopefully wake up Futures in order

    @Plugin.listener()
    async def on_guild_remove(self, guild):
        guild_id = guild.id

        try:
            self._tasks[guild_id].cancel()
        except KeyError:
            return

        for lookup in self._pending[guild_id]:
            lookup.set_result(None)

        del self._tasks[guild_id]
        del self._pending[guild_id]
