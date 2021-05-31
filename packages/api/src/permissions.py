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

import functools

import discord.flags
from starlette.exceptions import HTTPException

from .utils import find_request_parameter


def _has_permissions(request, **required):
    permissions = request.auth.bot_permissions
    return all(getattr(permissions, name) for name in required)


def has_permissions(**permissions):
    def decorator(func):
        idx = find_request_parameter(func)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request', args[idx])

            if not _has_permissions(request, **permissions):
                raise HTTPException(403, 'Missing required permissions to access route.')

            return await func(*args, **kwargs)

        return wrapper

    return decorator


@discord.flags.fill_with_flags()
class BotPermissions(discord.flags.BaseFlags):
    """
    Permissions which can be assigned to third-party integrations.

    Note that permissions are only created when an integration requires it,
    all other endpoints require the "administrator" permission for simplicity.
    """

    def __init__(self, value):
        super().__init__()
        self.value = value or 0

    @discord.flags.flag_value
    def administrator(self):
        return 1 << 0

    @discord.flags.flag_value
    def view_users(self):
        return 1 << 1

    @discord.flags.flag_value
    def edit_users(self):
        return 1 << 2
