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

import datetime

import discord
from discord.ext import commands


TRACKING_START = datetime.datetime(2021, 1, 16, tzinfo=datetime.timezone.utc)


class PruneDays(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            days = int(argument)
        except ValueError:
            raise commands.BadArgument(f'Days must be a positive integer greater or equal "7".')

        if days < 7:
            raise commands.BadArgument(f'Days must be a positive integer greater or equal "7".')

        start = max(ctx.guild.me.joined_at, TRACKING_START)

        now = discord.utils.utcnow()
        tracked = int((now - start).total_seconds() / 86400)

        if tracked > days:
            return days

        raise commands.BadArgument(
            f'Value is too large, status tracking has only been enabled for "{tracked}" days in this server.'
        )
