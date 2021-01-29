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

from starlette.exceptions import HTTPException

from .utils import find_request_parameter


def is_authorized(func):
    """Wraps a route and only allows authorized requests."""

    idx = find_request_parameter(func)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request', args[idx])

        if not request.user.is_authenticated:
            raise HTTPException(401, 'Authorization required.')

        return await func(*args, **kwargs)

    return wrapper
