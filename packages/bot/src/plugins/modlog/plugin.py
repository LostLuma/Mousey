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

from ... import NotFound, Plugin
from .emitter import Emitter, EmitterInactive


def timestamp():
    return datetime.datetime.utcnow().strftime('[%H:%M:%S]')


class ModLog(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self._configs = {}
        self._emitters = {}

    def cog_unload(self):
        for emitter in self._emitters.values():
            emitter.stop()

    async def log(self, guild, event, content, *, target=None):
        config = await self._get_config(guild)
        content = f'`{timestamp()}` {content}'

        is_member = isinstance(target, discord.Member)

        for channel, events in tuple(config.items()):
            if events & event.value != event.value:
                continue

            if not channel.permissions_for(guild.me).send_messages:
                continue

            if is_member and channel.permissions_for(target).read_messages:
                mention = None
            else:
                mention = target

            try:
                self._get_emitter(channel).send(content, mention)
            except EmitterInactive:  # Channel was deleted
                del config[channel]

    def _get_emitter(self, channel):
        try:
            return self._emitters[channel.id]
        except KeyError:
            pass

        self._emitters[channel.id] = emitter = Emitter(channel)
        return emitter

    async def _get_config(self, guild):
        try:
            return self._configs[guild.id]
        except KeyError:
            pass

        try:
            resp = await self.mousey.api.get_guild_modlogs(guild.id)
        except NotFound:
            resp = []

        config = {}

        for data in resp:
            channel = guild.get_channel(data['channel_id'])

            if channel is not None:
                config[channel] = data['events']

        self._configs[guild.id] = config
        return config

    @Plugin.listener('on_mouse_guild_remove')
    @Plugin.listener('on_mouse_config_update')
    async def on_config_invalidate(self, event):
        try:
            del self._configs[event.guild.id]
        except KeyError:
            return

        for channel in event.guild.text_channels:
            emitter = self._emitters.get(channel.id)

            if emitter is not None:
                emitter.stop()

    @Plugin.listener()
    async def on_guild_channel_delete(self, channel):
        config = self._configs.get(channel.guild.id)

        if config is None:
            return

        try:
            del config[channel]
        except KeyError:
            return

        try:
            emitter = self._emitters.pop(channel.id)
        except KeyError:
            return

        emitter.stop()
