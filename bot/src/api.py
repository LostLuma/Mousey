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

import asyncio

from .config import API_TOKEN, API_URL


class HTTPException(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message

    def __repr__(self):
        return f'<HTTPException status={self.status} message="{self.message}">'


class NotFound(HTTPException):
    def __init__(self, message):
        super().__init__(404, message)


class APIClient:
    def __init__(self, session):
        self.session = session

    async def request(self, method, path, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Authorization'] = API_TOKEN

        for attempt in range(5):
            async with self.session.request(method, API_URL + path, **kwargs) as resp:
                is_json = 'application/json' in resp.headers.get('Content-Type')

                if is_json:
                    data = await resp.json()
                else:
                    data = await resp.text()

                if 200 <= resp.status <= 299:
                    return data

                if not is_json:
                    error = data
                else:
                    error = data['error']

                if resp.status == 404:
                    raise NotFound(error)

                if 500 <= resp.status <= 599:
                    delay = (attempt + 1) * 2
                    await asyncio.sleep(delay)

                    continue

                raise HTTPException(resp.status, error)
            raise HTTPException(resp.status, error)

    async def get_status(self):
        return await self.request('GET', '/status')

    async def set_status(self, shard_id, status):
        data = {'shard_id': shard_id, 'status': status}
        return await self.request('POST', '/status', json=data)
