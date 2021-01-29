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

import jwt
from starlette.authentication import AuthenticationBackend, AuthenticationError, BaseUser
from starlette.middleware.authentication import AuthenticationMiddleware

from ..config import JWT_KEY
from .cors import add_header
from .errors import on_http_error


add_header('Authorization')


class User(BaseUser):
    def __init__(self, data):
        self.id = data['id']

        self.name = data['name']
        self.discriminator = data['discriminator']

    # This is not documented,,
    @property
    def identity(self):
        raise NotImplementedError

    @property
    def is_authenticated(self):
        return True

    @property
    def display_name(self):
        return f'{self.name}#{self.discriminator}'


class MouseAuthError(AuthenticationError):
    def __init__(self, status=401, detail=None):
        self.status_code = status
        self.detail = detail or 'Authorization failed.'


class MouseAuthBackend(AuthenticationBackend):
    async def authenticate(self, request):
        try:
            token = request.headers['Authorization']
        except KeyError:
            return

        try:
            data = jwt.decode(token, str(JWT_KEY), algorithms=["HS512"])
        except jwt.InvalidTokenError:
            raise MouseAuthError(401, 'Invalid or expired authorization token.')

        token_id = data['idx']

        async with request.app.db.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT id, name, discriminator
                FROM users
                WHERE id = (SELECT user_id FROM authorization_tokens WHERE idx = $1)
                """,
                token_id,
            )

        if record is not None:
            return [], User(record)

        # Token was manually revoked or expired
        raise MouseAuthError(401, 'Expired authorization token.')


def register(app):
    app.add_middleware(AuthenticationMiddleware, backend=MouseAuthBackend(), on_error=on_http_error)
