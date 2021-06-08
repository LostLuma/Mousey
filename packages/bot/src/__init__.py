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

__version__ = '4.0a'

from .api import HTTPException, NotFound
from .bot import Mousey
from .checks import bot_has_guild_permissions, bot_has_permissions, disable_in_threads
from .command import Command, Group, command, group
from .config import API_TOKEN, API_URL, BOT_TOKEN, FERNET_KEY, PSQL_URL, REDIS_URL, SHARD_COUNT
from .converter import *
from .emoji import *
from .enums import LogType
from .errors import BannedUserNotFound, NoThreadChannels, VisibleCommandError
from .events import *
from .plugin import Plugin
