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
from ..utils import build_update_query, ensure_user, parse_expires_at


router = Router()


def serialize_reminder(data):
    data = dict(data)
    data['expires_at'] = data['expires_at'].isoformat()

    return data


@router.route('/reminders', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_reminders(request):
    try:
        shard_id = int(request.query_params['shard_id'])
        limit = int(request.query_params.get('limit', 1))
    except (KeyError, ValueError):
        raise HTTPException(400, 'Invalid or missing "shard_id" or "limit" query param.')

    async with request.app.db.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT id, user_id, guild_id, channel_id, thread_id, message_id, referenced_message_id, expires_at, message
            FROM reminders
            WHERE (guild_id >> 22) % $2 = $1
            ORDER BY expires_at ASC
            LIMIT $3
            """,
            shard_id,
            SHARD_COUNT,
            limit,
        )

    if records:
        return JSONResponse(list(map(serialize_reminder, records)))

    raise HTTPException(404, 'No upcoming reminders found.')


@router.route('/reminders', methods=['POST'])
@is_authorized
@has_permissions(administrator=True)
async def post_reminders(request):
    data = await request.json()

    try:
        user = data['user']
        guild_id = data['guild_id']

        channel_id = data['channel_id']
        thread_id = data.get('thread_id')

        message_id = data['message_id']
        referenced_message_id = data.get('referenced_message_id')

        expires_at = data['expires_at']
        message = data.get('message', 'something')
    except KeyError:
        raise HTTPException(
            400, 'Missing "user", "guild_id", "channel_id", "message_id", "expires_at", or "message" JSON field.'
        )

    expires_at = parse_expires_at(expires_at)

    async with request.app.db.acquire() as conn:
        await ensure_user(conn, user)

        reminder_id = await conn.fetchval(
            """
            INSERT INTO reminders (
              user_id, guild_id, channel_id, thread_id, message_id, referenced_message_id, expires_at, message
            )
            VALUES ($1, $2, $3, $4,$5, $6, $7, $8)
            RETURNING id
            """,
            user['id'],
            guild_id,
            channel_id,
            thread_id,
            message_id,
            referenced_message_id,
            expires_at,
            message,
        )

    return JSONResponse({'id': reminder_id})


@router.route('/reminders/{id:int}', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_reminders_next(request):
    reminder_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        record = await conn.fetchrow(
            """
            SELECT id, user_id, guild_id, channel_id, thread_id, message_id, referenced_message_id, expires_at, message
            FROM reminders
            WHERE id = $1
            """,
            reminder_id,
        )

    if record is not None:
        return JSONResponse(serialize_reminder(record))

    raise HTTPException(404, 'Reminder not found.')


@router.route('/reminders/{id:int}', methods=['PATCH'])
@is_authorized
@has_permissions(administrator=True)
async def patch_reminders_id(request):
    data = await request.json()
    reminder_id = request.path_params['id']

    message = data.get('message')
    expires_at = data.get('expires_at')

    if message is None and expires_at is None:
        raise HTTPException(400, 'Requires at least one of "message" or "expires_at" JSON field.')

    if expires_at is not None:
        expires_at = parse_expires_at(expires_at)

    names = []
    updates = []

    if message is not None:
        names.append('message')
        updates.append(message)

    if expires_at is not None:
        names.append('expires_at')
        updates.append(expires_at)

    query, idx = build_update_query(names)

    async with request.app.db.acquire() as conn:
        record = await conn.fetchrow(
            f"""
            UPDATE reminders
            SET {query}
            WHERE id = ${idx}
            RETURNING
              id, user_id, guild_id, channel_id, thread_id, message_id, referenced_message_id, expires_at, message
            """,
            *updates,
            reminder_id,
        )

    if record is None:
        raise HTTPException(404, 'Reminder not found.')

    return JSONResponse(serialize_reminder(record))


@router.route('/reminders/{id:int}', methods=['DELETE'])
@is_authorized
@has_permissions(administrator=True)
async def delete_reminders_id(request):
    reminder_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        status = await conn.execute('DELETE FROM reminders WHERE id = $1', reminder_id)

    if int(status.split()[1]):
        return JSONResponse({})

    raise HTTPException(404, 'Reminder not found.')


@router.route('/guilds/{guild_id:int}/members/{member_id:int}/reminders', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_guilds_id_members_id_reminders(request):
    guild_id = request.path_params['guild_id']
    member_id = request.path_params['member_id']

    async with request.app.db.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT id, user_id, guild_id, channel_id, thread_id, message_id, referenced_message_id, expires_at, message
            FROM reminders
            WHERE guild_id = $1 AND user_id = $2
            ORDER BY expires_at ASC
            """,
            guild_id,
            member_id,
        )

    if records:
        return JSONResponse(list(map(serialize_reminder, records)))

    raise HTTPException(404, 'Specified member has no upcoming reminders.')
