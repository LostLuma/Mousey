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
import typing

import discord
from discord.ext import tasks

from ... import Plugin


# Permissions required to purge messages in a channel
PERMISSIONS = discord.Permissions(view_channel=True, manage_messages=True, read_message_history=True)


def is_not_pinned(message):
    return not message.pinned


class PurgeConfig(typing.NamedTuple):
    channel_id: int
    max_age: datetime.timedelta


# TODO: Delete messages on time when interval is small
class AutoPurge(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self.do_purge.start()

    def cog_unload(self):
        self.do_purge.stop()

    @tasks.loop(hours=1)
    async def do_purge(self):
        await self.mousey.wait_until_ready()

        async with self.mousey.db.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT autopurge.channel_id, autopurge.max_age
                FROM autopurge
                JOIN channels ON autopurge.channel_id = channels.id
                WHERE (channels.guild_id >> 22) % $2 = $1
                """,
                self.mousey.shard_id,
                self.mousey.shard_count,
            )

        for record in records:
            config = PurgeConfig(**record)
            await self._do_channel_purge(config)

    async def _do_channel_purge(self, config):
        channel = self.mousey.get_channel(config.channel_id)

        if not channel.permissions_for(channel.guild.me).is_superset(PERMISSIONS):
            return

        before = datetime.datetime.utcnow() - config.max_age
        await channel.purge(before=before, check=is_not_pinned, limit=None)
