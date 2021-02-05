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


@router.route('/guilds/{guild_id:int}/modlogs', methods=['GET'])
@is_authorized
async def get_guilds_guild_id_modlogs(request):
    guild_id = request.path_params['guild_id']

    async with request.app.db.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT modlogs.channel_id, modlogs.events
            FROM modlogs
            JOIN channels ON modlogs.channel_id = channels.id
            WHERE channels.guild_id = $1
            """,
            guild_id,
        )

    if not records:
        raise HTTPException(404, 'No modlog channels found.')

    return JSONResponse(list(map(dict, records)))


@router.route('/guilds/{guild_id:int}/modlogs/{id:int}', methods=['PUT'])
@is_authorized
async def put_guilds_guild_id_modlogs_id(request):
    data = await request.json()
    channel_id = request.path_params['id']

    try:
        events = data['events']
    except KeyError:
        raise HTTPException(400, 'Missing "events" JSON field.')

    async with request.app.db.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO modlogs (channel_id, events)
            VALUES ($1, $2)
            ON CONFLICT (channel_id) DO UPDATE
            SET events = EXCLUDED.events
            """,
            channel_id,
            events,
        )

    return JSONResponse({})


@router.route('/guilds/{guild_id:int}/modlogs/{id:int}', methods=['DELETE'])
@is_authorized
async def delete_guilds_guild_id_modlogs_id(request):
    channel_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        status = await conn.execute('DELETE FROM modlogs WHERE channel_id = $1', channel_id)

    if int(status.split()[1]):
        return JSONResponse({})

    raise HTTPException(404, 'Modlog channel not found.')
