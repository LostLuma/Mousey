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

import logging

import discord
from discord.ext import commands

from ... import Plugin
from .handler import get_message


log = logging.getLogger(__name__)


class Errors(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        mousey.on_error = self.on_error

    def cog_unload(self):
        self.mousey.on_error = commands.Bot.on_error

    async def on_error(self, event, *args, **kwargs):
        log.exception(f'Unhandled exception in {event} handler.')

    @Plugin.listener()
    async def on_command_error(self, ctx, error):
        hint = get_message(ctx, error)
        send = ctx.channel.permissions_for(ctx.me).send_messages

        if send and hint is not None:
            try:
                await ctx.send(hint)
            except discord.HTTPException:
                pass
