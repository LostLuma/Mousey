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

import aredis.lock
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.routing import Router

from ..auth import is_authorized
from ..config import SHARD_COUNT
from ..permissions import has_permissions
from ..utils import build_update_query, ensure_user, parse_expires_at


router = Router()


def serialize_infraction(record):
    data = dict(record)
    data['created_at'] = data['created_at'].isoformat()

    if data.get('expires_at') is not None:
        data['expires_at'] = data['expires_at'].isoformat()

    return data


@router.route('/infractions', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_infractions(request):
    try:
        shard_id = int(request.query_params['shard_id'])
    except (KeyError, ValueError):
        raise HTTPException(400, 'Invalid or missing "shard_id" query param.')

    # This only supports fetching the next expiring infraction for now
    async with request.app.db.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT id, guild_id, action, user_id, actor_id, reason, created_at, expires_at
            FROM infractions
            WHERE (guild_id >> 22) % $2 = $1 AND expires_at IS NOT NULL
            ORDER BY expires_at ASC
            LIMIT 1
            """,
            shard_id,
            SHARD_COUNT,
        )

    if records:
        return JSONResponse(list(map(serialize_infraction, records)))

    raise HTTPException(404, 'No expiring infractions found.')


@router.route('/guilds/{guild_id:int}/infractions', methods=['POST'])
@is_authorized
@has_permissions(administrator=True)
async def post_guilds_guild_id_infractions(request):
    data = await request.json()
    guild_id = request.path_params['guild_id']

    try:
        action = data['action']

        user = data['user']
        actor = data['actor']

        reason = data['reason']
        expires_at = data.get('expires_at')
    except KeyError:
        raise HTTPException(400, 'Missing "guild_id", "action", "user", "actor" or "reason" JSON field.')

    expires_at = parse_expires_at(expires_at)

    async with request.app.db.acquire() as conn:
        await ensure_user(conn, user)
        await ensure_user(conn, actor)

        # As far as I know there's no proper way to do a composite primary key
        # With one being a serial per the other value, so we manually increase
        # Infraction IDs in a lock to prevent inserting a value multiple times
        async with aredis.lock.Lock(request.app.redis, f'mousey:infraction-ids:{guild_id}'):
            previous = await conn.fetchval('SELECT max(id) FROM infractions WHERE guild_id = $1', guild_id)

            record = await conn.fetchrow(
                """
                INSERT INTO infractions (id, guild_id, action, user_id, actor_id, reason, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, guild_id, action, user_id, actor_id, reason, created_at, expires_at
                """,
                (previous or 0) + 1,
                guild_id,
                action,
                user['id'],
                actor['id'],
                reason,
                expires_at,
            )

    return JSONResponse(serialize_infraction(record))


@router.route('/guilds/{guild_id:int}/infractions/{id:int}', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_guilds_guild_id_infractions_id(request):
    inf_id = request.path_params['id']
    guild_id = request.path_params['guild_id']

    async with request.app.db.acquire() as conn:
        record = await conn.fetchrow(
            """
            SELECT id, guild_id, action, user_id, actor_id, reason, created_at, expires_at
            FROM infractions
            WHERE guild_id = $1 AND id = $2
            """,
            guild_id,
            inf_id,
        )

    return JSONResponse(serialize_infraction(record))


@router.route('/guilds/{guild_id:int}/infractions/{id:int}', methods=['PATCH'])
@is_authorized
@has_permissions(administrator=True)
async def patch_guilds_guild_id_infractions_id(request):
    data = await request.json()

    inf_id = request.path_params['id']
    guild_id = request.path_params['guild_id']

    reason = data.get('reason')
    expires_at = data.get('expires_at')

    if reason is None and expires_at is None:
        raise HTTPException(400, 'Requires at least one of "reason" or "expires_at" JSON field.')

    if expires_at is not None:
        expires_at = parse_expires_at(expires_at)

    names = []
    updates = []

    if reason is not None:
        names.append('reason')
        updates.append(reason)

    if expires_at is not None:
        names.append('expires_at')
        updates.append(expires_at)

    query, idx = build_update_query(names)

    async with request.app.db.acquire() as conn:
        record = await conn.fetchrow(
            f"""
            UPDATE infractions
            SET {query}
            WHERE guild_id = ${idx} AND id = ${idx + 1}
            RETURNING id, guild_id, action, user_id, actor_id, reason, created_at, expires_at
            """,
            *updates,
            guild_id,
            inf_id,
        )

    if record is not None:
        return JSONResponse(serialize_infraction(record))

    raise HTTPException(404, 'Infraction not found.')


@router.route('/guilds/{guild_id:int}/members/{member_id:int}/infractions', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_guilds_guild_id_members_member_id_infractions(request):
    guild_id = request.path_params['guild_id']
    user_id = request.path_params['member_id']

    async with request.app.db.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT id, guild_id, action, user_id, actor_id, reason, created_at, expires_at
            FROM infractions
            WHERE guild_id = $1 AND user_id = $2
            """,
            guild_id,
            user_id,
        )

    return JSONResponse(list(map(serialize_infraction, records)))
