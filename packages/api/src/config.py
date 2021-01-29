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

from starlette.config import Config
from starlette.datastructures import Secret


config = Config('.env')


JWT_KEY = config('JWT_KEY', cast=Secret)
FERNET_KEY = config('FERNET_KEY', cast=Secret)

# Database server URLs
PSQL_DSN = config('PSQL_DSN', cast=Secret)
REDIS_URL = config('REDIS_URL', cast=Secret)

SHARD_COUNT = config('SHARD_COUNT', cast=int)
