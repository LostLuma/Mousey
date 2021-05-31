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
from ..config import SHARD_COUNT
from ..permissions import has_permissions


router = Router()


@router.route('/guilds', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_guilds(request):
    try:
        shard_id = int(request.query_params['shard_id'])
    except (KeyError, ValueError):
        raise HTTPException(400, 'Invalid or missing "shard_id" query param.')

    async with request.app.db.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT id, name, icon
            FROM guilds
            WHERE (id >> 22) % $2 = $1 AND removed_at IS NULL
            """,
            shard_id,
            SHARD_COUNT,
        )

    return JSONResponse(list(map(dict, records)))


@router.route('/guilds/{id:int}', methods=['PUT'])
@is_authorized
@has_permissions(administrator=True)
async def put_guilds_id(request):
    data = await request.json()
    guild_id = request.path_params['id']

    try:
        name = data['name']
        icon = data['icon']

        roles = data['roles']
        channels = data['channels']
    except KeyError:
        raise HTTPException(400, 'Missing "name", "icon", "roles", or "channels" JSON field.')

    role_ids = [x['id'] for x in roles]
    channel_ids = [x['id'] for x in channels]

    async with request.app.db.acquire() as conn:
        exists = await conn.fetchval('SELECT true FROM guilds WHERE id = $1 AND removed_at IS NULL', guild_id)

        await conn.execute(
            """
            INSERT INTO guilds (id, name, icon)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name, icon = EXCLUDED.icon, removed_at = NULL
            """,
            guild_id,
            name,
            icon,
        )

        await conn.executemany(
            """
            INSERT INTO roles (id, guild_id, name, position, permissions)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name, position = EXCLUDED.position, permissions = EXCLUDED.permissions
            """,
            ((x['id'], guild_id, x['name'], x['position'], x['permissions']) for x in roles),
        )

        await conn.execute('DELETE FROM roles WHERE guild_id = $1 AND NOT id = ANY($2)', guild_id, role_ids)

        await conn.executemany(
            """
            INSERT INTO channels (id, guild_id, name, type)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE
            SET guild_id = EXCLUDED.guild_id, name = EXCLUDED.name, type = EXCLUDED.type
            """,
            ((x['id'], guild_id, x['name'], x['type']) for x in channels),
        )

        await conn.execute('DELETE FROM channels WHERE guild_id = $1 AND NOT id = ANY($2)', guild_id, channel_ids)

    return JSONResponse({'created': not exists})


@router.route('/guilds/{guild_id:int}/roles/{id:int}', methods=['PUT'])
@is_authorized
@has_permissions(administrator=True)
async def put_guilds_guild_id_roles_id(request):
    data = await request.json()

    role_id = request.path_params['id']
    guild_id = request.path_params['guild_id']

    try:
        name = data['name']

        position = data['position']
        permissions = data['permissions']
    except KeyError:
        raise HTTPException(400, 'Missing "name", "position", or "permissions" JSON field.')

    async with request.app.db.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO roles (id, guild_id, name, position, permissions)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name, position = EXCLUDED.position, permissions = EXCLUDED.permissions
            """,
            role_id,
            guild_id,
            name,
            position,
            permissions,
        )

    return JSONResponse({})


@router.route('/guilds/{guild_id:int}/roles/{id:int}', methods=['DELETE'])
@is_authorized
@has_permissions(administrator=True)
async def delete_guilds_guild_id_roles_id(request):
    role_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        status = await conn.execute('DELETE FROM roles WHERE id = $1', role_id)

    if int(status.split()[1]):
        return JSONResponse({})

    raise HTTPException(404, 'Role not found.')


@router.route('/guilds/{guild_id:int}/channels/{id:int}', methods=['PUT'])
@is_authorized
@has_permissions(administrator=True)
async def put_guilds_guild_id_channels_id(request):
    data = await request.json()

    channel_id = request.path_params['id']
    guild_id = request.path_params['guild_id']

    try:
        name = data['name']
        channel_type = data['type']
    except KeyError:
        raise HTTPException(400, 'Missing "name" or "type" JSON field.')

    async with request.app.db.acquire() as conn:
        # Channels can apparently be moved between guilds
        # So .. just in case this ever happens update guild_id too
        await conn.execute(
            """
            INSERT INTO channels (id, guild_id, name, type)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE
            SET guild_id = EXCLUDED.guild_id, name = EXCLUDED.name, type = EXCLUDED.type
            """,
            channel_id,
            guild_id,
            name,
            channel_type,
        )

    return JSONResponse({})


@router.route('/guilds/{guild_id:int}/channels/{id:int}', methods=['DELETE'])
@is_authorized
@has_permissions(administrator=True)
async def delete_guilds_guild_id_channels_id(request):
    channel_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        status = await conn.execute('DELETE FROM channels WHERE id = $1', channel_id)

    if int(status.split()[1]):
        return JSONResponse({})

    raise HTTPException(404, 'Channel not found.')


@router.route('/guilds/{id:int}', methods=['DELETE'])
@is_authorized
@has_permissions(administrator=True)
async def delete_guilds_id(request):
    guild_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        status = await conn.execute('UPDATE guilds SET removed_at = NOW() WHERE id = $1', guild_id)

    if int(status.split()[1]):
        return JSONResponse({})

    raise HTTPException(404, 'Guild not found.')
