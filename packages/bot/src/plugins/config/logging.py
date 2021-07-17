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
import inspect
import re

import discord

from ... import ExitableMenu, LogType, NotFound, disable_when_pressed
from ...utils import join_parts


DEFAULT_EVENTS = -1 & ~LogType.MEMBER_NAME_CHANGE.value


def format_event_names(data):
    if data['events'] == -1:
        return 'everything'

    if data['events'] == DEFAULT_EVENTS:
        return 'default (name changes disabled)'

    names = []

    for event in LogType:
        if data['events'] & event.value == event.value:
            names.append(event.name)

    if len(names) < 10:
        extra = ''
    else:
        extra = f' (and {len(names) - 10} others)'

    return ', '.join(names[:10]).replace('_', ' ').title() + extra


def match_channel(guild):
    def converter(argument):
        match = re.match(r'<?#?(\d{15,21})>?', argument)

        if match is not None:
            channel_id = int(match.group(1))
            return guild.get_channel(channel_id)

        return discord.utils.get(guild.text_channels, name=argument)

    return converter


def match_indexes(maximum):
    def converter(argument):
        numbers = argument.split()
        return all(x.isdigit() for x in numbers) and max(int(x) for x in numbers) <= maximum

    return converter


class LoggingMenu(ExitableMenu):
    async def get_content(self):
        data = await self.get_data()

        if not data:
            active = 'No log channels configured.'
        else:
            channels = []

            for item in data:
                channel = self.guild.get_channel(item['channel_id'])
                channels.append(f'{channel} - {format_event_names(item)}')

            channels.sort()
            active = f'Active log channels:{join_parts(channels)}'

        content = inspect.cleandoc(
            """
            **__Logging Configuration__**

            {active}

            You can add up to 10 log channels.
            """
        )

        return content.format(active=active)

    async def update_components(self):
        data = await self.get_data()

        if not data:
            self.add_log_channel.disabled = False
            self.modify_log_channel.disabled = True
            self.remove_log_channel.disabled = True
        elif len(data) > 10:
            self.add_log_channel.disabled = True
            self.modify_log_channel.disabled = False
            self.remove_log_channel.disabled = False
        else:
            self.add_log_channel.disabled = False
            self.modify_log_channel.disabled = False
            self.remove_log_channel.disabled = False

    async def get_data(self):
        try:
            return await self.mousey.api.get_guild_modlogs(self.guild.id)
        except NotFound:
            return []

    @discord.ui.button(label='Add Log Channel', style=discord.ButtonStyle.primary)
    @disable_when_pressed
    async def add_log_channel(self, button, interaction):
        check = match_channel(self.guild)

        try:
            response = await self.prompt(
                'Send the name, mention, or ID of the channel to set add.', check=check, interaction=interaction
            )
        except asyncio.TimeoutError:
            return

        channel = check(response)
        await self.upsert_logging_channel(channel, interaction=interaction)

    @discord.ui.button(label='Modify Log Channel', style=discord.ButtonStyle.primary)
    @disable_when_pressed
    async def modify_log_channel(self, button, interaction):
        try:
            channel = await self.pick_existing_channel('Select a log channel to modify.', interaction=interaction)
        except asyncio.TimeoutError:
            return

        await self.upsert_logging_channel(channel, interaction=interaction)

    async def upsert_logging_channel(self, channel, interaction):
        choices = ['default', 'everything', 'custom']

        message = inspect.cleandoc(
            """
            Choose how to configure this log channel:

            `default`: Logs every event in this channel
            `everything`: Logs all `default` events and name changes
            `custom`: Log specific events here
            """
        )

        try:
            mode = await self.choose(message, choices=choices, interaction=interaction)
        except asyncio.TimeoutError:
            return

        if mode == 'everything':
            events = -1
        elif mode == 'default':
            events = DEFAULT_EVENTS
        else:
            choices = {x: event for x, event in enumerate(LogType)}
            names = '\n'.join(str(x) + ' ' + e.name.replace('_', ' ').title() for x, e in choices.items())

            try:
                response = await self.prompt(
                    f'Respond with the indexes of events to log:\n\n'
                    f'{names}\n\nPlease separate the indexes by spaces: `20 21 22`',
                    check=match_indexes(max(choices)),
                    interaction=interaction,
                )
            except asyncio.TimeoutError:
                return

            events = 0

            for index in response.split():
                events |= choices[int(index)].value

        await self.mousey.api.set_channel_modlogs(self.guild.id, channel.id, events)

        config = self.mousey.get_cog('Config')
        config.dispatch_config_update(self.guild)

    @discord.ui.button(label='Remove Log Channel', style=discord.ButtonStyle.danger)
    @disable_when_pressed
    async def remove_log_channel(self, button, interaction):
        try:
            channel = await self.pick_existing_channel('Select a log channel to remove.', interaction=interaction)
        except asyncio.TimeoutError:
            return

        await self.mousey.api.delete_channel_modlogs(self.guild.id, channel.id)

        config = self.mousey.get_cog('Config')
        config.dispatch_config_update(self.guild)

    async def pick_existing_channel(self, message, interaction):
        options = []
        data = await self.get_data()

        for item in data:
            channel = self.guild.get_channel(item['channel_id'])
            options.append(discord.SelectOption(label=channel.name, value=channel.id))

        options = sorted(options, key=lambda x: x.label)
        channel_id = await self.pick(message, options=options, interaction=interaction)

        return self.guild.get_channel(int(channel_id))
