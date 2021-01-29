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

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse


HANDLERS = []


def add_handler(exception):
    def decorator(func):
        HANDLERS.append((exception, func))
        return func

    return decorator


@add_handler(Exception)
def on_internal_error(request, error):
    return JSONResponse({'error': 'Internal Server Error.'}, 500)


@add_handler(HTTPException)
def on_http_error(request, error):
    stop = '' if error.detail.endswith('.') else '.'
    return JSONResponse({'error': error.detail + stop}, error.status_code)


@add_handler(json.JSONDecodeError)
def on_json_error(request, error):
    return JSONResponse({'error': 'Invalid JSON body.'}, 400)


# See https://www.starlette.io/exceptions
# The ExceptionMiddleware is already added to the app
def register(app):
    for args in HANDLERS:
        app.add_exception_handler(*args)
