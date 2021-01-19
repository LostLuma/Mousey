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

from starlette.middleware.cors import CORSMiddleware


CORS_HEADERS = []
CORS_MAX_AGE = 86400
CORS_METHODS = ['DELETE', 'GET', 'PATCH', 'POST', 'PUT']


def add_header(name):
    CORS_HEADERS.append(name)


def register(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex='.*',  # Always return Origin header as Access-Control-Allow-Origin to allow credentials
        allow_methods=CORS_METHODS,
        allow_headers=CORS_HEADERS,
        max_age=CORS_MAX_AGE,
    )
