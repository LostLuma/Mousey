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

from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route, Router

from . import (
    archives,
    autoprune,
    autopurge,
    guilds,
    infractions,
    modlog,
    permissions,
    prefixes,
    reminders,
    roles,
    statistics,
    status,
    templates,
    users,
)


def get_root(request):
    return PlainTextResponse('beep boop')


def extract_routes(*modules):
    # Mounting multiple routers with a common prefix only allows using routes from the first router.
    # To avoid this issue we simply extract all routes from each module and add them with a single mount.
    routes = []

    for module in modules:
        routes.extend(module.router.routes)

    return routes


router = Router(
    [
        Route('/', get_root),
        Mount(
            '/v4',
            routes=extract_routes(
                archives,
                autoprune,
                autopurge,
                guilds,
                infractions,
                modlog,
                permissions,
                prefixes,
                reminders,
                roles,
                statistics,
                status,
                templates,
                users,
            ),
        ),
    ]
)
