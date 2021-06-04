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

from ..errors import BannedUserNotFound


def action_reason(argument):
    if len(argument) <= 1000:
        return argument

    raise commands.BadArgument('Reason must be 1000 or fewer characters.')


class SafeUser(commands.Converter):
    """
    Tries to convert to a member or user from a mention, ID, or exact DiscordTag match.
    This converter should be used in all moderation commands to ensure targets are chosen correctly.

    Note that when no cached member or user is found for an ID a discord.Object is returned,
    to allow using eg. the ban command with a large collection of IDs without the converter failing due to invalid ones.
    """

    async def convert(self, ctx, argument):
        match = re.match(r'(?:<@!?)?(\d{15,21})>?', argument)

        if match is not None:
            user_id = int(match.group(1))
            member = ctx.guild.get_member(user_id)

            if member is not None:
                return member

            return ctx.bot.get_user(user_id) or discord.Object(id=user_id)

        match = re.match(r'(.{2,32})#(\d{4})', argument)

        if match is not None:
            name, discriminator = match.groups()
            member = discord.utils.get(ctx.guild.members, name=name, discriminator=discriminator)

            if member is not None:
                return member

            raise commands.UserNotFound(argument)

        raise commands.BadArgument(f'Unable to parse "{argument}" as a mention, ID, or DiscordTag.')


def _banned_users(bans):
    for ban in bans:
        yield ban.user


class SafeBannedUser(commands.Converter):
    """
    Tries to convert to a banned user from a mention, ID, or exact DiscordTag match.

    Note that when no banned member or user is found for an ID a discord.Object is returned,
    to allow using eg. the ban command with a large collection of IDs without the converter failing due to invalid ones.
    """

    async def convert(self, ctx, argument):
        match = re.match(r'(?:<@!?)?(\d{15,21})>?', argument)

        if match is not None:
            user_id = int(match.group(1))
            user = discord.Object(id=user_id)

            try:
                ban = await ctx.guild.fetch_ban(user)
            except discord.NotFound:
                return user

            return ban.user

        match = re.match(r'(.{2,32})#(\d{4})', argument)

        if match is not None:
            bans = await ctx.guild.bans()
            name, discriminator = match.groups()

            user = discord.utils.get(_banned_users(bans), name=name, discriminator=discriminator)

            if user is not None:
                return user

            raise BannedUserNotFound(argument)

        raise commands.BadArgument(f'Unable to parse "{argument}" as a mention, ID, or DiscordTag.')
