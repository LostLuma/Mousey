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

import os


# beep boop
BOT_TOKEN = os.environ['BOT_TOKEN']
# Message encryption key
FERNET_KEY = os.environ['FERNET_KEY']

# Database server URLs
PSQL_URL = os.environ['PSQL_DSN']
REDIS_URL = os.environ['REDIS_URL']

SHARD_COUNT = int(os.environ['SHARD_COUNT'])
