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
import typing

import discord

from ... import GuildChangeEvent, NotFound, Plugin
from ...utils import serialize_user


# Channel types Mousey uses
_ChannelType = discord.ChannelType
CHANNEL_TYPES = {_ChannelType.category, _ChannelType.text, _ChannelType.news, _ChannelType.voice}


def serialize_role(role):
    data = {
        'id': role.id,
        'name': role.name,
        'position': role.position,
        'permissions': role.permissions.value,
    }

    return data


def serialize_channel(channel):
    data = {
        'id': channel.id,
        'name': channel.name,
        'type': channel.type.value,
    }

    return data


class PartialGuild(typing.NamedTuple):
    id: int

    name: str
    icon: str

    def __str__(self):
        return self.name


class State(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        if mousey.is_ready():
            asyncio.create_task(self.on_ready())

    # Guilds

    @Plugin.listener()
    async def on_ready(self):
        # See which guilds we left while disconnected

        resp = await self.mousey.api.get_guilds(self.mousey.shard_id)

        for data in resp:
            guild = self.mousey.get_guild(data['id'])

            if guild is not None:
                continue

            guild = PartialGuild(**data)
            await self.mousey.api.delete_guild(guild.id)

            event = GuildChangeEvent(guild)
            self.mousey.dispatch('mouse_guild_remove', event)

    @Plugin.listener('on_guild_join')
    @Plugin.listener('on_guild_available')
    async def on_guild_create(self, guild):
        await self._update_guild(guild)

    @Plugin.listener()
    async def on_guild_update(self, before, after):
        await self._update_guild(after)

    async def _update_guild(self, guild):
        channels = [x for x in guild.channels if x.type in CHANNEL_TYPES]

        data = {
            'id': guild.id,
            'name': guild.name,
            'icon': guild.icon and guild.icon.key,
            'roles': list(map(serialize_role, guild.roles)),
            'channels': list(map(serialize_channel, channels)),
        }

        resp = await self.mousey.api.create_guild(data)

        if resp['created']:
            event = GuildChangeEvent(guild)
            self.mousey.dispatch('mouse_guild_join', event)

    @Plugin.listener()
    async def on_guild_remove(self, guild):
        await self.mousey.api.delete_guild(guild.id)

        event = GuildChangeEvent(guild)
        self.mousey.dispatch('mouse_guild_remove', event)

    # Roles

    @Plugin.listener()
    async def on_guild_role_create(self, role):
        await self._create_role(role)

    @Plugin.listener()
    async def on_guild_role_update(self, before, after):
        if before.name != after.name or before.position != after.position or before.permissions != after.permissions:
            await self._create_role(after)

    async def _create_role(self, role):
        data = serialize_role(role)

        try:
            await self.mousey.api.create_role(role.guild.id, data)
        except NotFound:
            pass

    @Plugin.listener()
    async def on_guild_role_delete(self, role):
        try:
            await self.mousey.api.delete_role(role.guild.id, role.id)
        except NotFound:
            pass

    # Channels

    @Plugin.listener()
    async def on_guild_channel_create(self, channel):
        if channel.type not in CHANNEL_TYPES:
            return

        await self._create_channel(channel)

    @Plugin.listener()
    async def on_guild_channel_update(self, before, after):
        if after.type not in CHANNEL_TYPES:
            return

        if before.guild == after.guild and before.name == after.name and before.type == after.type:
            return

        await self._create_channel(after)

    async def _create_channel(self, channel):
        data = serialize_channel(channel)

        try:
            await self.mousey.api.create_channel(channel.guild.id, data)
        except NotFound:
            pass

    @Plugin.listener()
    async def on_guild_channel_delete(self, channel):
        try:
            await self.mousey.api.delete_channel(channel.guild.id, channel.id)
        except NotFound:
            pass

    # Users

    @Plugin.listener()
    async def on_member_join(self, member):
        await self._update_user(member)

    @Plugin.listener()
    async def on_user_update(self, before, after):
        await self._update_user(after)

    async def _update_user(self, user):
        data = serialize_user(user)

        try:
            await self.mousey.api.update_user(data)
        except NotFound:
            pass
