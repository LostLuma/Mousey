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
from typing import Any, Dict

import discord

from ... import NotFound, Plugin
from ...utils import create_task
from .buttons import RoleButtonAction, RoleChangeButton, RoleListButton
from .view import TemplateView


def get_id_information(custom_id):
    match = re.match(r'(?:\d{15,21}-)?(\d{15,21})-(.*)', custom_id)

    if match is None:
        return

    snowflake = match.group(1)
    button_action = match.group(2)

    return int(snowflake), button_action


# Bot permissions required to set up and use a template channel
PERMISSIONS = discord.Permissions(
    view_channel=True, send_messages=True, manage_messages=True, read_message_history=True
)


class Templates(Plugin):
    """
    Allows server admins to create channel content templates (with buttons!).

    For simplicity sake other users' messages are not allowed in these channels.
    """

    def __init__(self, mousey):
        super().__init__(mousey)

        self._active_channels = set()

        if not mousey.is_ready():
            return

        for guild in mousey.guilds:
            create_task(self.on_guild_available(guild))

    def cog_unload(self):
        for view in self.persisted_views():
            view.stop()

    def bot_check(self, ctx):
        return ctx.channel.id not in self._active_channels

    def persisted_views(self):
        for view in self.mousey.persistent_views:
            if isinstance(view, TemplateView):
                yield view

    @Plugin.listener()
    async def on_message(self, message):
        if message.author.id == self.mousey.user.id:
            return

        if message.channel.id in self._active_channels:
            await message.delete()

    @Plugin.listener()
    async def on_guild_available(self, guild):
        try:
            data = await self.mousey.api.get_templates(guild.id)
        except NotFound:
            return

        for template in data:
            channel = guild.get_channel(template['channel_id'])
            await self.add_channel(channel, template['data'], update=False)

    @Plugin.listener()
    async def on_guild_remove(self, guild):
        for channel in guild.text_channels:
            self.remove_channel(channel)

    @Plugin.listener()
    async def on_guild_channel_delete(self, channel):
        self.remove_channel(channel)

    def remove_channel(self, channel):
        if channel.id in self._active_channels:
            for view in self.persisted_views():
                if view.channel_id == channel.id:
                    view.stop()

            self._active_channels.discard(channel.id)

    async def add_channel(self, channel, template, *, update):
        if update and not channel.permissions_for(channel.guild.me).is_superset(PERMISSIONS):
            return

        self._active_channels.add(channel.id)

        # The role list button requires all role IDs up front
        # Construct a list of all assigable roles in this channel
        role_ids = {}

        for entry in template:
            for button in entry.get('buttons', []):
                role_id = button.get('role_id')

                if role_id is not None:
                    role_ids[role_id] = None

        # Messages are sent in one batch to prevent the username + timestamp showing
        # If the count stayed the same messages are edited, otherwise they are re-sent
        messages = []
        replace = False

        if update:
            async for message in channel.history():
                if message.author.id != self.mousey.user.id:
                    await message.delete()
                else:
                    messages.insert(0, message)

            # Re-send due to differing counts
            if len(messages) != len(template):
                replace = True
                update = False

                await channel.delete_messages(messages)

        for idx, entry in enumerate(template):
            if update and not self._message_was_updated(entry, messages[idx]):
                continue

            kwargs: Dict[str, Any] = {
                'embeds': [],
                'view': None,
                'content': None,
                'allowed_mentions': discord.AllowedMentions(users=True),
            }

            if 'content' in entry:
                kwargs['content'] = entry['content']

            if 'embeds' in entry:
                kwargs['embeds'] = tuple(map(discord.Embed.from_dict, entry['embeds']))

            if 'buttons' in entry:
                kwargs['view'] = view = self._create_view(entry=entry, channel_id=channel.id, role_ids=role_ids)
                self.mousey.add_view(view)  # When not replacing or updating after a reboot add persistent views

            if replace:
                await channel.send(**kwargs)
            elif update:
                await messages[idx].edit(**kwargs)

    def _create_view(self, *, entry, channel_id, role_ids):
        view = TemplateView(channel_id)

        for data in entry['buttons']:
            kwargs = {
                'row': data['row'],
                'label': data['label'],
                'channel_id': channel_id,
            }

            if 'emoji' in data:
                kwargs['emoji'] = discord.PartialEmoji(**data['emoji'])

            if data['action'] == 'role-list':
                button = RoleListButton(role_ids=role_ids, **kwargs)
            else:
                action = RoleButtonAction(data['action'][5:])  # "role-assign", "role-toggle" etc.
                button = RoleChangeButton(mousey=self.mousey, action=action, role_id=data['role_id'], **kwargs)

            view.add_item(button)

        return view

    def _message_was_updated(self, updates, message):
        # Re-create the template data from an existing message and compare
        # This is kind of ugly, but allows us to only update changed entries
        data: Dict[str, Any] = {
            'type': 'message',
        }

        if message.content:
            data['content'] = message.content

        if message.embeds:
            embeds = []

            for embed in message.embeds:
                embed = embed.to_dict()
                embed_type = embed.pop('type')

                if embed_type == 'rich':
                    embeds.append(embed)

            if embeds:
                data['embeds'] = embeds

        if message.components:
            data['buttons'] = buttons = []

            for idx, row in enumerate(message.components):
                for button in row.children:
                    result = get_id_information(button.custom_id)

                    if result is None:
                        return True

                    snowflake, action = result

                    kwargs = {
                        'row': idx,
                        'action': action,
                        'label': button.label,
                    }

                    if action != 'role-list':
                        kwargs['role_id'] = snowflake

                    if button.emoji:
                        kwargs['emoji'] = button.emoji.to_dict()

                    buttons.append(kwargs)

        return data != updates
