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

from ...utils import populate_methods


@populate_methods(discord.Attachment)
class Attachment:
    __slots__ = ('_http', 'channel_id', 'filename', 'id')

    def __init__(self, path, state):
        match = re.match(r'/attachments/(\d{15,21})/(\d{15,21})/(.+)', path)

        self.channel_id = int(match.group(1))

        self.id = int(match.group(2))
        self.filename = match.group(3)

        self._http = state.http  # Required for read() etc. methods to work

    @property
    def url(self):
        return f'https://cdn.discordapp.com/attachments/{self.channel_id}/{self.id}/{self.filename}'

    @property
    def proxy_url(self):
        return f'https://media.discordapp.net/attachments/{self.channel_id}/{self.id}/{self.filename}'


@populate_methods(discord.Message)
class Message:
    __slots__ = ('attachments', 'author', 'channel', 'content', 'deleted_at', 'edited_at', 'embeds', 'id')

    def __init__(self, **kwargs):
        self.id = kwargs['id']

        self.author = kwargs['author']
        self.channel = kwargs['channel']

        self.content = kwargs['content']

        self.embeds = list(map(discord.Embed.from_dict, kwargs['embeds']))
        self.attachments = [Attachment(path=x, state=self._state) for x in kwargs['attachments']]

        self.edited_at = kwargs['edited_at']
        self.deleted_at = kwargs['deleted_at']

    def __repr__(self):
        return f'<Message id={self.id}>'

    # Properties don't get copied with @populate_methods

    @property
    def created_at(self):
        return discord.utils.snowflake_time(self.id)

    @property
    def guild(self):
        return self.channel.guild

    @property
    def jump_url(self):
        return f'https://discordapp.com/channels/{self.guild.id}/{self.channel.id}/{self.id}'

    # Required for added methods to function

    @property
    def _state(self):
        # noinspection PyProtectedMember
        return self.channel._state

    def _update(self, *args, **kwargs):
        pass
