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

import aiohttp
import discord

from ...utils import create_task


EMPTY_MESSAGE_ERROR = 50006


class EmitterInactive(Exception):
    pass


class Emitter:
    __slots__ = ('buffer', 'channel', 'last_emit', 'task')

    def __init__(self, channel: discord.TextChannel) -> None:
        self.buffer: list[tuple[str, discord.abc.Snowflake | None]] = []
        self.channel: discord.TextChannel = channel

        self.last_emit: float = 0
        self.task: asyncio.Task[None] = create_task(self._emit())

    @property
    def active(self) -> bool:
        return not self.task.cancelled()

    def send(self, content: str, mention: discord.abc.Snowflake | None = None) -> None:
        if not self.active:
            raise EmitterInactive

        for line in content.splitlines():
            self.buffer.append((line, mention))

        if self.task.done():
            self.task = create_task(self._emit())

    def stop(self) -> None:
        self.task.cancel()

    def _get_message(self) -> tuple[str, discord.AllowedMentions]:
        parts: list[str] = []
        mentions: list[discord.abc.Snowflake | None] = []

        length: int = 0
        collecting: bool = True

        while collecting and self.buffer:
            line_length = len(self.buffer[0][0])

            if length + line_length + 1 > 2000:
                collecting = False
            else:
                length += line_length + 1
                content, mention = self.buffer.pop(0)

                parts.append(content)
                mentions.append(mention)

        return '\n'.join(parts), discord.AllowedMentions(users=list(filter(None, mentions)))

    async def _emit(self) -> None:
        while self.buffer:
            # Wait before emitting to send fewer messages overall:
            # - if we haven't emitted recently wait 100ms in case more is queued
            # - if we have sent recently wait until 1s has passed, to roughly send at the ~5/5s rate limit
            passed = time.perf_counter() - self.last_emit
            await asyncio.sleep(1 - passed if passed < 1 else 0.1)

            self.last_emit = time.perf_counter()
            content, mentions = self._get_message()

            try:
                await self.channel.send(content, silent=True, allowed_mentions=mentions)
            except discord.NotFound:  # :strawberrysad:
                self.stop()
            except (asyncio.TimeoutError, aiohttp.ClientError, discord.Forbidden, discord.DiscordServerError):
                pass
            except discord.HTTPException as e:
                if e.code != EMPTY_MESSAGE_ERROR:  # Discord rarely returns this despite content being present
                    raise
