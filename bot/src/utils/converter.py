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

import re

import discord
from discord.ext import commands


class SafeUser(commands.Converter):
    """Attempts to convert to a member or user from a mention, ID, or DiscordTag match."""

    async def convert(self, ctx, argument):
        match = re.match(r'(?:<@!?)?(\d{15,21})>?', argument)

        if match is not None:
            user_id = int(match.group(1))
            member = ctx.guild.get_member(user_id)

            if member is not None:
                return member

            try:
                return ctx.bot.get_user(user_id) or await ctx.bot.fetch_user(user_id)
            except discord.NotFound:
                raise commands.UserNotFound(argument)

        match = re.match(r'(.{2,32})#(\d{4})', argument)

        if match is not None:
            name, discriminator = match.groups()
            member = discord.utils.get(ctx.guild.members, name=name, discriminator=discriminator)

            if member is not None:
                return member

        raise commands.UserNotFound(argument)
