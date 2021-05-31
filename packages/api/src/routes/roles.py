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

import discord
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.routing import Router

from ..auth import is_authorized
from ..permissions import has_permissions


router = Router()


def enabled_permissions(permissions):
    for name, value in dict(permissions).items():
        if value:
            yield name.replace('_', ' ')


PRIVILEGED_PERMISSIONS = discord.Permissions(
    administrator=True,
    ban_members=True,
    deafen_members=True,
    kick_members=True,
    manage_channels=True,
    manage_emojis=True,
    manage_guild=True,
    manage_messages=True,
    manage_nicknames=True,
    manage_roles=True,
    manage_webhooks=True,
    mention_everyone=True,
    move_members=True,
    mute_members=True,
)


@router.route('/guilds/{guild_id:int}/groups', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_guilds_guild_id_groups(request):
    guild_id = request.path_params['guild_id']

    async with request.app.db.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT groups.role_id, groups.description
            FROM groups
            JOIN roles ON groups.role_id = roles.id
            WHERE roles.guild_id = $1
            """,
            guild_id,
        )

    if not records:
        raise HTTPException(404, 'No groups found.')

    return JSONResponse(list(map(dict, records)))


@router.route('/guilds/{guild_id:int}/groups/{id:int}', methods=['PUT'])
@is_authorized
@has_permissions(administrator=True)
async def put_guilds_guild_id_groups_id(request):
    data = await request.json()
    role_id = request.path_params['id']

    try:
        description = data['description']
    except KeyError:
        raise HTTPException(400, 'Missing "description" JSON field.')

    async with request.app.db.acquire() as conn:
        permissions = await conn.fetchval('SELECT permissions FROM roles WHERE id = $1', role_id)
        privileged = discord.Permissions(PRIVILEGED_PERMISSIONS.value & permissions)  # Filter enabled in both

        if privileged.value:
            raise HTTPException(400, 'Role has privileged permissions: ' + ', '.join(enabled_permissions(privileged)))

        await conn.execute(
            """
            INSERT INTO groups (role_id, description)
            VALUES ($1, $2)
            ON CONFLICT (role_id) DO UPDATE
            SET description = EXCLUDED.description
            """,
            role_id,
            description,
        )

    return JSONResponse({})


@router.route('/guilds/{guild_id:int}/groups/{id:int}', methods=['DELETE'])
@is_authorized
@has_permissions(administrator=True)
async def delete_guilds_guild_id_groups_id(request):
    role_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        status = await conn.execute('DELETE FROM groups WHERE role_id = $1', role_id)

    if int(status.split()[1]):
        return JSONResponse({})

    raise HTTPException(404, 'Group not found.')
