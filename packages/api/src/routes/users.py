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


@router.route('/users/{id:int}', methods=['PATCH'])
@is_authorized
@has_permissions(edit_users=True)
async def patch_users_id(request):
    data = await request.json()
    user_id = request.path_params['id']

    try:
        name = data['name']
        discriminator = data['discriminator']
        avatar = data['avatar']
    except KeyError:
        raise HTTPException(400, 'Missing "name", "discriminator", or "avatar" JSON field.')

    async with request.app.db.acquire() as conn:
        status = await conn.execute(
            'UPDATE users SET name = $1, discriminator = $2, avatar = $3 WHERE id = $4',
            name,
            discriminator,
            avatar,
            user_id,
        )

    if int(status.split()[1]):
        return JSONResponse({})

    raise HTTPException(404, 'User not found.')
