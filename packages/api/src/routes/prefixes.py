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

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.routing import Router

from ..auth import is_authorized
from ..permissions import has_permissions


router = Router()


@router.route('/guilds/{id:int}/prefixes', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_guilds_id_prefixes(request):
    guild_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        prefixes = await conn.fetchval('SELECT prefixes FROM prefixes WHERE guild_id = $1', guild_id)

    if prefixes:
        return JSONResponse(prefixes)

    raise HTTPException(404, 'No custom prefixes found.')


@router.route('/guilds/{id:int}/prefixes', methods=['PUT'])
@is_authorized
@has_permissions(administrator=True)
async def put_guilds_id_prefixes(request):
    prefixes = await request.json()
    guild_id = request.path_params['id']

    prefixes = sorted(prefixes, reverse=True)

    async with request.app.db.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO prefixes (guild_id, prefixes)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE
            SET prefixes = EXCLUDED.prefixes
            """,
            guild_id,
            prefixes,
        )

    return JSONResponse({})
