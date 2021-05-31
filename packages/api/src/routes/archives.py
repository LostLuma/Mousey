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

import re

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.routing import Router

from ..auth import is_authorized
from ..permissions import has_permissions
from ..utils import decrypt_json, encrypt_json, generate_snowflake


router = Router()


# TODO: Ensure user is some form of mod in guild
# TODO: Support channel, role mentions in content
@router.route('/archives/{id:int}', methods=['GET'])
async def get_archives_id(request):
    archive_id = request.path_params['id']

    async with request.app.db.acquire() as conn:
        record = await conn.fetchrow('SELECT guild_id, messages, user_ids FROM archives WHERE id = $1', archive_id)

    if record is None:
        raise HTTPException(404, 'Archive not found.')

    guild_id = record['guild_id']
    user_ids = record['user_ids']
    messages = decrypt_json(record['messages'])

    async with request.app.db.acquire() as conn:
        user_records = await conn.fetch(
            'SELECT id, bot, name, discriminator, avatar FROM users WHERE id = ANY($1)', user_ids
        )

        channel_records = await conn.fetch('SELECT id, name FROM channels WHERE guild_id = $1', guild_id)

    users = {x['id']: dict(x) for x in user_records}
    channels = {x['id']: dict(x) for x in channel_records}

    results = []

    for message in messages:
        message = dict(message)

        author_id = message.pop('author_id')
        message['author'] = users[author_id]

        channel_id = message.pop('channel_id')
        message['channel'] = channels.get(channel_id)

        content = message['content']
        message['mentions'] = mentions = {}

        for user_id in re.findall(r'<@!?(\d{15,21})>', content):
            mentions[user_id] = users.get(int(user_id))

        results.append(message)

    return JSONResponse({'messages': results})


@router.route('/archives', methods=['POST'])
@is_authorized
@has_permissions(administrator=True)
async def post_archives_id(request):
    data = await request.json()
    archive_id = generate_snowflake()

    try:
        guild_id = data['guild_id']
        messages = data['messages']
    except KeyError:
        raise HTTPException(400, 'Missing "guild_id" or "messages" JSON field.')

    # Remove full users/channels before storing
    # Up to date versions are injected on fetch
    users = {}

    for message in messages:
        author = message.pop('author')
        mentions = message.pop('mentions')

        message['author_id'] = author['id']

        for user in (author, *mentions):
            user_id = user['id']
            users[user_id] = user

        channel = message.pop('channel')
        message['channel_id'] = channel['id']

    messages = encrypt_json(messages)

    async with request.app.db.acquire() as conn:
        await conn.execute(
            'INSERT INTO archives (id, guild_id, messages, user_ids) VALUES ($1, $2, $3, $4)',
            archive_id,
            guild_id,
            messages,
            users.keys(),
        )

        await conn.executemany(
            """
            INSERT INTO users (id, bot, name, discriminator, avatar)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name, discriminator = EXCLUDED.discriminator, avatar = EXCLUDED.avatar
            """,
            ((x['id'], x['bot'], x['name'], x['discriminator'], x['avatar']) for x in users.values()),
        )

    return JSONResponse({'id': archive_id})
