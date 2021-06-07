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

from ... import NotFound, Plugin


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

        try:
            resp = await self.mousey.api.get_autopurge(self.mousey.shard_id)
        except NotFound:
            return

        for config in resp:
            config['max_age'] = datetime.timedelta(seconds=config['max_age'])

            config = PurgeConfig(**config)
            await self._do_channel_purge(config)

    async def _do_channel_purge(self, config):
        channel = self.mousey.get_channel(config.channel_id)

        if channel is None:
            return

        if not channel.permissions_for(channel.guild.me).is_superset(PERMISSIONS):
            return

        before = discord.utils.utcnow() - config.max_age
        await channel.purge(before=before, check=is_not_pinned, limit=None)
