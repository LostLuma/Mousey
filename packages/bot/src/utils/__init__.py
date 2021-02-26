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

from .asyncio import create_task
from .converter import SafeUser
from .formatting import Plural, code_safe, describe, describe_user, user_name
from .helpers import has_membership_screening, populate_methods, serialize_user
from .logging import setup_logging
from .paginator import PaginatorInterface, close_interface_context
from .sql import PGSQL_ARG_LIMIT, multirow_insert
from .time import TimeConverter, human_delta
