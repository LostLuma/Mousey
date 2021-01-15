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
import pathlib

import aiohttp
import aredis.lock
import asyncpg
import discord
from discord.ext import commands

from . import __version__
from .config import BOT_TOKEN, PSQL_URL, REDIS_URL, SHARD_COUNT
from .context import Context
from .utils import create_task


async def wait_redis_connected(redis):
    while True:
        try:
            await redis.get('cheese')
        except aredis.BusyLoadingError:
            await asyncio.sleep(0.5)
        else:
            return


async def get_prefix(mousey, message):
    config = mousey.get_cog('Config')
    base = [f'<@{mousey.user.id}> ', f'<@!{mousey.user.id}> ']

    if config is None:
        return base  # Always return valid prefixes

    return base + await config.get_prefixes(message.guild)


class Mousey(commands.Bot):
    def __init__(self):
        activity = discord.Game('beep boop')
        allowed_mentions = discord.AllowedMentions.none()

        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            invites=True,
            voice_states=True,
            presences=True,
            guild_messages=True,
            guild_reactions=True,
            guild_typing=True,
        )

        super().__init__(
            activity=activity,
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            command_prefix=get_prefix,
            guild_ready_timeout=10,
            help_command=None,
            intents=intents,
            max_messages=None,
            shard_id=None,
            shard_count=SHARD_COUNT,
        )

        self.db = None
        self.redis = None

        self.session = None

        self.shard_task = None

    def run(self):
        super().run(BOT_TOKEN)

    async def start(self, *args, **kwargs):
        self.db = await asyncpg.create_pool(PSQL_URL)
        self.redis = redis = aredis.StrictRedis.from_url(REDIS_URL)

        await wait_redis_connected(redis)  # :blobpain:

        self.session = aiohttp.ClientSession(
            headers={'User-Agent': f'Mousey/{__version__} (+https://github.com/SnowyLuma/Mousey)'}
        )

        plugins = ['jishaku']
        base = pathlib.Path('./bot/plugins')

        for path in base.glob('*/__init__.py'):
            plugins.append(str(path.parent).replace('/', '.'))

        for plugin in plugins:
            self.load_extension(plugin)

        await self.set_shard_id()
        await super().start(*args, **kwargs)

    async def close(self):
        try:
            await super().close()
        finally:
            self.shard_task.cancel()

            await self.db.close()
            self.redis.connection_pool.disconnect()

    async def process_commands(self, message):
        if message.author.bot:
            return

        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)

    async def before_identify_hook(self, shard_id, *, initial=False):
        await aredis.lock.Lock(self.redis, 'mousey:identify', timeout=5.5).acquire()

    # This is probably not a very ideal way of assigning shards
    # However docker-compose doesn't give us any help as to which container # we are

    # The bot claims a shard ID by setting an expiring value in Redis
    # When the process exits the value expires and can be claimed again

    async def set_shard_id(self):
        while self.shard_id is None:
            await self._set_shard_id()

        self.shard_task = create_task(self._keep_shard_id())

    async def _set_shard_id(self):
        for shard_id in range(SHARD_COUNT):
            success = await self.redis.set(f'mousey:shards:{shard_id}', 'beep', ex=10, nx=True)

            if not success:
                continue

            self.shard_id = shard_id

    async def _keep_shard_id(self):
        while True:
            await asyncio.sleep(5)
            await self.redis.set(f'mousey:shards:{self.shard_id}', 'beep', ex=10)
