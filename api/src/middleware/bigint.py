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

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

from .cors import add_header


add_header('X-No-BigInt')


ENABLED_SYMBOLS = ('true', '1')


class BigIntMiddleware(BaseHTTPMiddleware):
    """
    Middleware to transform all large integers in JSON responses to strings when a client requests it.
    This is done as JavaScript's JSON.parse can't handle integers >= 53 bits which eg. snowflakes are.

    Browsers sending the Origin header will have this behavior applied automatically, other clients
    Requiring this sort of behavior can simply set the X-No-BigInt header to "true" or "1" on all requests.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        json = response.headers.get('Content-Type') == 'application/json'
        enabled = request.headers.get('Origin') or request.headers.get('X-No-BigInt') in ENABLED_SYMBOLS

        if enabled and json:
            # The original UJSONResponse is wrapped into a StreamingResponse by Starlette
            # To re-create the originally returned JSON body we iterate over the internal body iterator,
            # As calling the response would also run background tasks and ultimately delay the response.
            chunks = []

            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    chunks.append(chunk)
                else:  # Chunks may be bytes
                    chunks.append(chunk.decode('utf-8'))

            original = ''.join(chunks)

            # This might replace unwanted parts inside strings,
            # However I don't want to fix this in all clients yet
            content = re.sub(r'":\s?(\d{16,})', r'":"\1"', original)

            # Remove Content-Length header as the content is most likely longer now
            headers = {name: value for name, value in response.headers.items() if name != 'content-length'}

            response = PlainTextResponse(
                content,
                status_code=response.status_code,
                headers=headers,
                background=response.background,
            )

        return response


def register(app):
    app.add_middleware(BigIntMiddleware)
