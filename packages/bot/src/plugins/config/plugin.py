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

import typing

from discord.ext import commands

from ... import ConfigUpdateEvent, NotFound, Plugin, bot_has_permissions, group
from .logging import LoggingMenu
from .prefixes import PrefixMenu


class PermissionConfig(typing.NamedTuple):
    required_roles: typing.List[int] = []

    def to_dict(self):
        data = {
            'required_roles': self.required_roles,
        }

        return data


class Config(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self._prefixes = {}
        self._permissions = {}

        self._max_concurrency = commands.MaxConcurrency(1, per=commands.BucketType.channel, wait=False)

    def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator

    async def cog_before_invoke(self, ctx):
        await self._max_concurrency.acquire(ctx)

    async def cog_after_invoke(self, ctx):
        await self._max_concurrency.release(ctx)

    async def bot_check(self, ctx):
        permissions = await self.get_permissions(ctx.guild)

        if not permissions.required_roles:
            return True

        author = ctx.author.guild_permissions
        return author.administrator or any(x.id in permissions.required_roles for x in ctx.author.roles)

    @group(aliases=['settings'], enabled=False)
    async def config(self, ctx):
        pass

    @config.command()
    @bot_has_permissions(send_messages=True)
    async def logging(self, ctx):
        """
        Configure logging-related settings.

        The menu opened by this command allows you to:
        \N{BULLET} Add and modify logging channels
        \N{BULLET} Remove existing logging channels

        Example: `{prefix}config logging`
        """

        await LoggingMenu(context=ctx).start()

    @config.command()
    @bot_has_permissions(send_messages=True)
    async def prefixes(self, ctx):
        """
        Configure custom command prefixes.

        The menu opened by this command allows you to:
        \N{BULLET} Add new prefixes
        \N{BULLET} Remove existing prefixes

        Example: `{prefix}config prefixes`
        """

        await PrefixMenu(context=ctx).start()

    @Plugin.listener()
    async def on_mouse_config_update(self, event):
        try:
            del self._prefixes[event.guild.id]
        except KeyError:
            pass

    def dispatch_config_update(self, guild):
        event = ConfigUpdateEvent(guild)
        self.mousey.dispatch('mouse_config_update', event)

    async def get_prefixes(self, guild):
        try:
            return self._prefixes[guild.id]
        except KeyError:
            pass

        try:
            prefixes = await self.mousey.api.get_prefixes(guild.id)
        except NotFound:
            prefixes = []

        self._prefixes[guild.id] = prefixes
        return prefixes

    async def set_prefixes(self, guild, prefixes):
        prefixes = sorted(set(prefixes), reverse=True)

        self._prefixes[guild.id] = prefixes
        await self.mousey.api.set_prefixes(guild.id, prefixes)

    async def get_permissions(self, guild):
        try:
            return self._permissions[guild.id]
        except KeyError:
            pass

        try:
            permissions = await self.mousey.api.get_permissions(guild.id)
        except NotFound:
            permissions = {}

        self._permissions[guild.id] = permissions = PermissionConfig(**permissions)
        return permissions

    async def set_permissions(self, guild, permissions):
        self._permissions[guild.id] = permissions
        await self.mousey.api.set_permissions(guild.id, permissions.to_dict())
