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
import time


class Lookup:
    """Represents a pending audit log lookup."""

    __slots__ = ('_future', 'action', 'check', 'expires_at', 'target')

    def __init__(self, action, target, check, timeout):
        self._future = asyncio.Future()

        self.action = action
        self.check = check
        self.target = target

        self.expires_at = time.monotonic() + timeout

    @property
    def expired(self):
        return time.monotonic() > self.expires_at or self._future.cancelled()

    def matches(self, entry):
        if entry.action != self.action:
            return False

        if self.target and entry.target.id != self.target.id:
            return False

        if self.check is None:
            return True

        return self.check(entry)

    def wait(self):
        return self._future

    def set_result(self, result):
        try:
            self._future.set_result(result)
        except asyncio.InvalidStateError:
            pass  # This Lookup is cancelled
