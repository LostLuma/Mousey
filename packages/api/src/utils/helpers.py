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

import datetime
import inspect

from starlette.exceptions import HTTPException


# Code taken from Starlette's @requires decorator
def find_request_parameter(func):
    signature = inspect.signature(func)

    for idx, parameter in enumerate(signature.parameters.values()):
        if parameter.name == 'request':
            return idx

    raise TypeError(f'Unable to locate "request" parameter.')


async def ensure_user(connection, user):
    await connection.execute(
        """
        INSERT INTO users (id, bot, name, discriminator, avatar)
        VALUES  ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name, discriminator = EXCLUDED.discriminator, avatar = EXCLUDED.avatar
        """,
        user['id'],
        user['bot'],
        user['name'],
        user['discriminator'],
        user['avatar'],
    )


def parse_expires_at(value):
    if value is None:
        return

    try:
        expires_at = datetime.datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, 'Invalid "expires_at" JSON field value.')

    if expires_at > datetime.datetime.utcnow() + datetime.timedelta(days=365 * 10):
        raise HTTPException(400, 'Invalid "expires_at" JSON field value. Must be less than ten years into the future.')

    return expires_at
