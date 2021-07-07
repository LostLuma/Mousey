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

import discord

from ... import MemberRoleChangeEvent
from ...utils import code_safe


class RoleButtonAction(discord.Enum):
    assign = 'assign'
    remove = 'remove'
    toggle = 'toggle'


class RoleChangeButton(discord.ui.Button):
    def __init__(self, *, mousey, action, channel_id, role_id, **kwargs):
        if action is RoleButtonAction.assign:
            style = discord.ButtonStyle.success
        elif action is RoleButtonAction.remove:
            style = discord.ButtonStyle.danger
        else:
            style = discord.ButtonStyle.primary

        custom_id = f'{channel_id}-{role_id}-role-{action.name}'
        super().__init__(style=style, custom_id=custom_id, **kwargs)

        self.mousey = mousey

        self.action = action
        self.role_id = role_id

    async def callback(self, interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id)

        if role is None:
            await interaction.response.send_message('Role associated with button not found.', ephemeral=True)
            return

        if not guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(f'I\'m missing permissions to manage roles.', ephemeral=True)
            return

        if role >= guild.me.top_role:
            await interaction.response.send_message(f'My top role is too low to manage this role.', ephemeral=True)
            return

        has_role = any(x.id == self.role_id for x in interaction.user.roles)

        if self.action is RoleButtonAction.toggle:
            add_role = not has_role
        else:
            add_role = self.action is RoleButtonAction.assign

        if add_role:
            if not has_role:
                await self._change_role(interaction, role, True)

            content = f'You\'ve been added to the `{code_safe(role)}` role.'
        else:
            if has_role:
                await self._change_role(interaction, role, False)

            content = f'You\'ve been removed from the `{code_safe(role)}` role.'

        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=True)
        else:
            await interaction.response.send_message(content, ephemeral=True)

    async def _change_role(self, interaction, role, assign):
        if assign:
            event_name = 'mouse_role_add'
            change_role = interaction.user.add_roles
        else:
            event_name = 'mouse_role_remove'
            change_role = interaction.user.remove_roles

        reason = 'Template role button usage'
        events = self.mousey.get_cog('Events')

        event = MemberRoleChangeEvent(interaction.user, role, interaction.guild.me, reason)
        events.ignore(interaction.guild, event_name, event)

        # Always call response.defer() as
        # Interactions have timed out before
        await asyncio.gather(
            interaction.response.defer(),
            change_role(role, reason=reason),
        )

        self.mousey.dispatch(event_name, event)


class RoleListButton(discord.ui.Button):
    def __init__(self, *, channel_id, role_ids, **kwargs):
        super().__init__(style=discord.ButtonStyle.secondary, custom_id=f'{channel_id}-role-list', **kwargs)

        self.role_ids = role_ids

    async def callback(self, interaction):
        roles = tuple(filter(None, map(interaction.user.get_role, self.role_ids)))

        if not roles:
            await interaction.response.send_message('You have not assigned any roles at the moment!', ephemeral=True)
        else:
            await interaction.response.send_message(
                'You currently have the following roles:\n\n' + '\n'.join(map(code_safe, roles)), ephemeral=True
            )
