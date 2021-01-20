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

from starlette.responses import JSONResponse
from starlette.routing import Router

from ..config import SHARD_COUNT


router = Router()


DEFAULT_STATUS = {'ready': False, 'latency': None}


@router.route('/status', methods=['GET'])
async def get_status(request):
    shards = {}
    values = await request.app.redis.mget(f'mousey:shards:{x}' for x in range(SHARD_COUNT))

    for shard_id, data in enumerate(values):
        if data is None:
            shards[shard_id] = DEFAULT_STATUS
        else:
            shards[shard_id] = json.loads(data)

    return JSONResponse({'shards': shards})
