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
import typing

import discord
from discord.ext import tasks

from ... import Plugin


# Channel types Mousey uses
_ChannelType = discord.ChannelType
CHANNEL_TYPES = {_ChannelType.category, _ChannelType.text, _ChannelType.news, _ChannelType.voice}


class PartialGuild(typing.NamedTuple):
    id: int

    name: str
    icon: str

    def __str__(self):
        return self.name


class State(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self.remove_stale_data.start()

        if mousey.is_ready():
            asyncio.create_task(self.on_ready())

    def cog_unload(self):
        self.remove_stale_data.start()

    # Guilds

    @Plugin.listener('on_ready')
    async def on_ready(self):
        # See which guilds we left while disconnected

        async with self.mousey.db.acquire() as conn:
            records = await conn.fetch(
                'SELECT id, name, icon FROM guilds WHERE (id >> 22) % $2 = $1',
                self.mousey.shard_id,
                self.mousey.shard_count,
            )

        for record in records:
            guild = self.mousey.get_guild(record['id'])

            if guild is not None:
                continue

            guild = PartialGuild(**record)
            self.mousey.dispatch('mouse_guild_remove', guild)

    @Plugin.listener('on_guild_join')
    @Plugin.listener('on_guild_available')
    async def on_guild_create(self, guild):
        async with self.mousey.db.acquire() as conn:
            exists = await conn.fetchval('SELECT true FROM guilds WHERE id = $1', guild.id)

            await conn.execute(
                """
                INSERT INTO guilds (id, name, icon)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name, icon = EXCLUDED.icon
                """,
                guild.id,
                guild.name,
                guild.icon,
            )

        if not exists:
            self.mousey.dispatch('mouse_guild_join', guild)

        await self._sync_guild_channels(guild)

    @Plugin.listener()
    async def on_guild_update(self, before, after):
        if before.name == after.name and before.icon == after.icon:
            return

        async with self.mousey.db.acquire() as conn:
            await conn.execute('UPDATE guilds SET name = $1, icon = $2 WHERE id = $3', after.name, after.icon, after.id)

    @Plugin.listener()
    async def on_guild_remove(self, guild):
        async with self.mousey.db.acquire() as conn:
            await conn.execute('UPDATE guilds SET removed_at = NOW() WHERE id = $1', guild.id)

        self.mousey.dispatch('mouse_guild_remove', guild)

    # Channels

    @Plugin.listener()
    async def on_guild_channel_create(self, channel):
        if channel.type not in CHANNEL_TYPES:
            return

        async with self.mousey.db.acquire() as conn:
            await conn.execute(
                'INSERT INTO channels (id, guild_id, name, type) VALUES ($1, $2, $3, $4)',
                channel.id,
                channel.guild.id,
                channel.name,
                channel.type.value,
            )

    @Plugin.listener()
    async def on_guild_channel_update(self, before, after):
        if after.type not in CHANNEL_TYPES:
            return

        if before.guild == after.guild and before.name == after.name and before.type == after.type:
            return

        async with self.mousey.db.acquire() as conn:
            await conn.execute(
                'UPDATE channels SET guild_id = $1, name = $2, type = $3 WHERE id = $4',
                after.guild.id,
                after.name,
                after.type.value,
                after.id,
            )

    @Plugin.listener()
    async def on_guild_channel_delete(self, channel):
        if channel.type not in CHANNEL_TYPES:
            return

        async with self.mousey.db.acquire() as conn:
            await conn.execute('DELETE FROM channels WHERE id = $1', channel.id)

    async def _sync_guild_channels(self, guild):
        async with self.mousey.db.acquire() as conn:
            # Add missing / Update channels
            channels = (x for x in guild.channels if x.type in CHANNEL_TYPES)

            await conn.executemany(
                """
                INSERT INTO channels (id, guild_id, name, type)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE
                SET guild_id = EXCLUDED.guild_id, name = EXCLUDED.name, type = EXCLUDED.type
                """,
                ((x.id, guild.id, x.name, x.type.value) for x in channels),
            )

            # Remove channels deleted during downtime
            records = await conn.fetch('SELECT id FROM channels WHERE guild_id = $1', guild.id)

            removed = []

            for record in records:
                channel = guild.get_channel(record['id'])

                if channel is None:
                    removed.append(record['id'])

            if removed:
                await conn.execute('DELETE FROM channels WHERE id = ANY($1)', removed)

    # Users

    @Plugin.listener()
    async def on_member_join(self, member):
        await self._update_user(member)

    @Plugin.listener()
    async def on_user_update(self, before, after):
        await self._update_user(after)

    async def _update_user(self, user):
        async with self.mousey.db.acquire() as conn:
            await conn.execute(
                'UPDATE users SET name = $1, discriminator = $2, avatar = $3 WHERE id = $4',
                user.name,
                user.discriminator,
                user.avatar,
                user.id,
            )

    # Background tasks

    @tasks.loop(hours=24)
    async def remove_stale_data(self):
        async with self.mousey.db.acquire() as conn:
            await conn.execute("DELETE FROM guilds WHERE removed_at < NOW() - '3 months'::INTERVAL")
