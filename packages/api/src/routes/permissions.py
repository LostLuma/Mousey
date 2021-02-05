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


router = Router()


@router.route('/guilds/{id:int}/permissions', methods=['GET'])
@is_authorized
async def get_guilds_id_prefixes(request):
    guild_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        required_roles = await conn.fetchval('SELECT required_roles FROM required_roles WHERE guild_id = $1', guild_id)

    if required_roles:
        return JSONResponse(required_roles)

    raise HTTPException(404, 'No permissions found.')


@router.route('/guilds/{id:int}/permissions', methods=['PUT'])
@is_authorized
async def put_guilds_id_prefixes(request):
    data = await request.json()
    guild_id = request.path_params['id']

    try:
        required_roles = data['required_roles']
    except KeyError:
        raise HTTPException(400, 'Missing "required_roles" JSON field.')

    async with request.app.db.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO required_roles (guild_id, required_roles)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE
            SET required_roles = EXCLUDED.required_roles
            """,
            guild_id,
            required_roles,
        )

    return JSONResponse({})
