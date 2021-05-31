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

import json

import aiohttp
import aredis
import asyncpg
from starlette.applications import Starlette

from .config import PSQL_DSN, REDIS_URL
from .middleware import register_middleware
from .routes import router


app = Starlette()

app.db = None
app.redis = None

app.session = None

app.mount('/', router)
register_middleware(app)


async def init_pg_connection(conn):
    # https://magicstack.github.io/asyncpg/current/usage.html#example-automatic-json-conversion
    await conn.set_type_codec(typename='jsonb', schema='pg_catalog', encoder=json.dumps, decoder=json.loads)


@app.on_event('startup')
async def on_startup():
    app.redis = aredis.StrictRedis.from_url(str(REDIS_URL))
    app.db = await asyncpg.create_pool(str(PSQL_DSN), init=init_pg_connection)

    app.session = aiohttp.ClientSession(headers={'User-Agent': f'Mousey/4.0 (+https://github.com/LostLuma/Mousey)'})


@app.on_event('shutdown')
async def on_shutdown():
    await app.db.close()
    await app.session.close()

    app.redis.connection_pool.disconnect()
