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
import logging


log = logging.getLogger(__name__)


def set_none_result(future):
    try:
        future.set_result(None)
    except asyncio.InvalidStateError:
        pass


def create_task(coro):
    """Wraps asyncio.create_task to log on exception."""

    task = asyncio.create_task(coro)
    task.add_done_callback(_log_exc)

    return task


def call_later(delay, callback, *args):
    """Execute call_later without getting the event loop."""

    return asyncio.get_event_loop().call_later(delay, callback, *args)


def _log_exc(task):
    try:
        error = task.exception()
    except asyncio.CancelledError:
        return

    if error is not None:
        log.exception(f'Unexpected exception in task {task!r}.', exc_info=error)
