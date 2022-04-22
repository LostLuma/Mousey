# -*- coding: utf-8 -*-

"""
Mousey: Discord Moderation Bot
Copyright (C) 2016 - 2022 Lilly Rose Berner

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
from typing import Callable, Optional, Union

import discord


CheckFunction = Callable[[discord.AuditLogEntry], bool]


def _default_check(entry: discord.AuditLogEntry) -> bool:
    return True


class Lookup:
    """Represents an unfulfilled audit log lookup."""

    __slots__ = ('_future', 'action', 'check', 'expires_at', 'target')

    def __init__(
        self,
        action: discord.AuditLogAction,
        target: Optional[discord.abc.Snowflake],
        check: Optional[CheckFunction],
        timeout: float,
    ):
        self.action: discord.AuditLogAction = action
        self.check: CheckFunction = check or _default_check
        self.target: Optional[discord.abc.Snowflake] = target

        self.expires_at: float = time.monotonic() + timeout

        self._future: asyncio.Future[Union[discord.AuditLogEntry, None]] = asyncio.get_event_loop().create_future()

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at

    def matches(self, entry: discord.AuditLogEntry) -> bool:
        if entry.action is not self.action:
            return False

        if self.target and (entry.target and entry.target.id) != self.target.id:
            return False

        return self.check(entry)

    def wait(self) -> asyncio.Future[Union[discord.AuditLogEntry, None]]:
        return self._future

    def set_result(self, result: Union[discord.AuditLogEntry, None]) -> None:
        try:
            self._future.set_result(result)
        except asyncio.InvalidStateError:
            pass  # Lookup has been cancelled
