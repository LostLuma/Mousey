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

    # Archives

    async def create_archive(self, guild_id, messages):
        data = {'guild_id': guild_id, 'messages': messages}
        return await self.request('POST', '/archives', json=data)

    # Autoprune

    async def get_autoprune(self, shard_id):
        params = {'shard_id': shard_id}
        return await self.request('GET', '/autoprune', params=params)

    # Autopurge

    async def get_autopurge(self, shard_id):
        params = {'shard_id': shard_id}
        return await self.request('GET', '/autopurge', params=params)

    # Guilds

    async def get_guild(self, guild_id):
        return await self.request('GET', f'/guilds/{guild_id}')

    async def get_guilds(self, shard_id):
        params = {'shard_id': shard_id}
        return await self.request('GET', '/guilds', params=params)

    async def create_guild(self, data):
        guild_id = data['id']
        return await self.request('PUT', f'/guilds/{guild_id}', json=data)

    async def create_role(self, guild_id, data):
        role_id = data['id']
        return await self.request('PUT', f'/guilds/{guild_id}/roles/{role_id}', json=data)

    async def delete_role(self, guild_id, role_id):
        return await self.request('DELETE', f'/guilds/{guild_id}/roles/{role_id}')

    async def create_channel(self, guild_id, data):
        channel_id = data['id']
        return await self.request('PUT', f'/guilds/{guild_id}/channels/{channel_id}', json=data)

    async def delete_channel(self, guild_id, channel_id):
        return await self.request('DELETE', f'/guilds/{guild_id}/channels/{channel_id}')

    async def delete_guild(self, guild_id):
        return await self.request('DELETE', f'/guilds/{guild_id}')

    # Modlog

    async def get_guild_modlogs(self, guild_id):
        return await self.request('GET', f'/guilds/{guild_id}/modlogs')

    async def set_channel_modlogs(self, guild_id, channel_id, events):
        data = {'events': events}
        return await self.request('PUT', f'/guilds/{guild_id}/modlogs/{channel_id}', json=data)

    async def delete_channel_modlogs(self, guild_id, channel_id):
        return await self.request('DELETE', f'/guilds/{guild_id}/modlogs/{channel_id}')

    # Permissions

    async def get_permissions(self, guild_id):
        return await self.request('GET', f'/guilds/{guild_id}/permissions')

    async def set_permissions(self, guild_id, data):
        return await self.request('PUT', f'/guilds/{guild_id}/permissions', json=data)

    # Prefixes

    async def get_prefixes(self, guild_id):
        return await self.request('GET', f'/guilds/{guild_id}/prefixes')

    async def set_prefixes(self, guild_id, prefixes):
        return await self.request('PUT', f'/guilds/{guild_id}/prefixes', json=prefixes)

    # Reminders

    async def get_reminders(self, shard_id, limit=1):
        params = {'shard_id': shard_id, 'limit': limit}
        return await self.request('GET', '/reminders', params=params)

    async def get_reminder(self, reminder_id):
        return await self.request('GET', f'/reminders/{reminder_id}')

    async def create_reminder(self, data):
        return await self.request('POST', '/reminders', json=data)

    async def update_reminder(self, reminder_id, data):
        return await self.request('PATCH', f'/reminders/{reminder_id}', json=data)

    async def delete_reminder(self, reminder_id):
        return await self.request('DELETE', f'/reminders/{reminder_id}')

    async def get_member_reminders(self, guild_id, member_id):
        return await self.request('GET', f'/guilds/{guild_id}/members/{member_id}/reminders')

    # Roles

    async def get_groups(self, guild_id):
        return await self.request('GET', f'/guilds/{guild_id}/groups')

    async def create_group(self, guild_id, role_id, data):
        return await self.request('PUT', f'/guilds/{guild_id}/groups/{role_id}', json=data)

    async def delete_group(self, guild_id, role_id):
        return await self.request('DELETE', f'/guilds/{guild_id}/groups/{role_id}')

    # Status

    async def get_status(self):
        return await self.request('GET', '/status')

    async def set_status(self, shard_id, status):
        data = {'shard_id': shard_id, 'status': status}
        return await self.request('POST', '/status', json=data)

    # Users

    async def update_user(self, data):
        user_id = data['id']
        return await self.request('PATCH', f'/users/{user_id}', json=data)
