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


@router.route('/guilds/{id:int}/templates', methods=['GET'])
@is_authorized
@has_permissions(administrator=True)
async def get_guilds_id_templates(request):
    guild_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT templates.channel_id, templates.data
            FROM templates
            JOIN channels ON templates.channel_id = channels.id
            WHERE channels.guild_id = $1
            """,
            guild_id,
        )

    if records:
        return JSONResponse(list(map(dict, records)))

    raise HTTPException(404, 'No channel templates found.')
