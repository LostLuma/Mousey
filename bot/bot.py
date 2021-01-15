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

import pathlib

import aiohttp
import aredis
import asyncpg
import discord
from discord.ext import commands

from . import __version__
from .config import BOT_TOKEN, PSQL_URL, REDIS_URL
from .context import Context


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
            shard_id=0,
            shard_count=1,
        )

        self.db = None
        self.redis = None

        self.session = None

    def run(self):
        super().run(BOT_TOKEN)

    async def start(self, *args, **kwargs):
        self.db = await asyncpg.create_pool(PSQL_URL)
        self.redis = aredis.StrictRedis.from_url(REDIS_URL)

        self.session = aiohttp.ClientSession(
            headers={'User-Agent': f'Mousey/{__version__} (+https://github.com/SnowyLuma/Mousey)'}
        )

        plugins = ['jishaku']
        base = pathlib.Path('./bot/plugins')

        for path in base.glob('*/__init__.py'):
            plugins.append(str(path.parent).replace('/', '.'))

        for plugin in plugins:
            self.load_extension(plugin)

        await super().start(*args, **kwargs)

    async def close(self):
        try:
            await super().close()
        finally:
            await self.db.close()
            self.redis.connection_pool.disconnect()

    async def process_commands(self, message):
        if message.author.bot:
            return

        ctx = await self.get_context(message, cls=Context)
        await self.invoke(ctx)
