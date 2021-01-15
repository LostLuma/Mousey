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
import datetime
import inspect
import re
import typing

import discord

from ... import Plugin, bot_has_permissions, group
from ...utils import Plural, code_safe
from .converter import guild_prefix


def match_role_ids(message):
    role_ids = re.findall(r'(?:<@&)?(\d{15,21})>?', message.content)

    if role_ids:
        return list(map(int, role_ids))


class GuildConfig(typing.NamedTuple):
    prefixes: typing.List[str] = []
    required_roles: typing.List[int] = []


# TODO
# modlog setup
# prefix management
class Config(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self._configs = {}

    def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator

    async def bot_check(self, ctx):
        config = await self._get_config(ctx.guild)

        if not config.required_roles:
            return True

        permissions = ctx.author.guild_permissions
        return permissions.administrator or any(x.id in config.required_roles for x in ctx.author.roles)

    @group(enabled=False)
    async def prefix(self, ctx):
        pass

    @prefix.command('add')
    async def prefix_add(self, ctx, prefix: guild_prefix):
        """
        Add a custom prefix which can be used with the bot.

        Prefix must be one word, or be quoted if it is not.

        Example: `{prefix}prefix add !`
        """

        config = await self._get_config(ctx.guild)
        prefixes = sorted([prefix, *config.prefixes], reverse=True)

        await self._update_prefixes(ctx.guild, prefixes)
        await ctx.send(f'Added `{code_safe(prefix)}` as a new prefix.')

    @prefix.command('remove')
    async def prefix_remove(self, ctx, prefix: guild_prefix):
        """
        Remove a custom prefix which is currently used.

        Prefix must be one word, or be quoted if it is not.

        Example: `{prefix}prefix remove !`
        """

        config = await self._get_config(ctx.guild)
        prefixes = config.prefixes

        try:
            prefixes.remove(prefix)
        except ValueError:
            await ctx.send(f'Prefix `{code_safe(prefix)}` is not in use.')
        else:
            await self._update_prefixes(ctx.guild, prefixes)
            await ctx.send(f'Removed `{code_safe(prefix)}` from server prefixes.')

    async def _update_prefixes(self, guild, prefixes):
        async with self.mousey.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guild_configs (guild_id, prefixes)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE
                SET prefixes = EXCLUDED.prefixes
                """,
                guild.id,
                prefixes,
            )

        self.mousey.dispatch('mouse_config_update', guild)

    @group()
    @bot_has_permissions(send_messages=True)
    async def autoprune(self, ctx):
        """
        View current autoprune settings.

        Example: `{prefix}autoprune`
        """

        async with self.mousey.db.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT role_ids, activity_type, inactive_timeout, updated_at
                FROM autoprune
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

        if record is None:
            await ctx.send('Autoprune is currently not set up. You can do so using the `autoprune setup` command.')
            return

        if not record['role_ids']:
            roles = 'without any roles'
        elif record['role_ids'] == [ctx.guild.id]:
            roles = 'regardless of roles (ignoring moderators)'
        else:
            mentions = ' '.join(f'<@&{x}>' for x in record['role_ids'])
            roles = f'having **one of** these roles: {mentions} (ignoring moderators)'

        if record['activity_type'] == 'joined':
            activity = 'the user\'s join date'
        elif record['activity_type'] == 'seen':
            activity = 'the user\'s activity in the server'
        else:
            activity = 'the user\'s activity on Discord (emulating built-in prune)'

        days = int(record['inactive_timeout'].total_seconds() / 86400)

        messages = [
            inspect.cleandoc(
                f"""
                Autoprune settings for {ctx.guild}:

                \N{BULLET} Removing users {roles}
                \N{BULLET} Inactivity is measured by {activity}
                \N{BULLET} Users are removed after being inactive for `{Plural(days):day}` or more\
                """
            )
        ]

        now = datetime.datetime.utcnow()
        if record['updated_at'] + record['inactive_timeout'] > now:
            messages.append(
                '\N{BULLET} Autoprune was set up too recently, '
                'users who I\'ve never seen will not be pruned yet \N{WARNING SIGN}'
            )

        messages.append('*Autoprune runs once every day, you might need to wait for it to go into effect.*')

        await ctx.send('\n\n'.join(messages))

    @autoprune.command('setup')
    @bot_has_permissions(send_messages=True)
    async def autoprune_setup(self, ctx):
        """
        Interactively set up an autoprune rule for the current server.

        Example: `{prefix}autoprune setup`
        """

        prefix = 'Autoprune setup - '

        def common_check(new):
            return new.channel == ctx.channel and new.author == ctx.author

        await ctx.send(f'{prefix}Please specify after how many days users should be pruned (must be more than 7 days):')

        def check(new):
            return common_check(new) and new.content.isdigit() and int(new.content) > 7

        try:
            result = await self.mousey.wait_for('message', check=check, timeout=60 * 5)
        except asyncio.TimeoutError:
            await ctx.send('Cancelled setup after inactivity.')
            return

        days = int(result.content)

        await ctx.send(
            inspect.cleandoc(
                f"""
                {prefix}Please specify how inactivity should be measured:

                `join date`: Inactive after being in the server for too long **this not recommended!**
                `server activity`: Inactive when not typing, sending messages, reacting etc.
                `discord activity`: Inactive when not active in server or online (emulates Discord's built-in prune)
                """
            )
        )

        choices = {
            'join date': 'joined',
            'server activity': 'seen',
            'discord activity': 'status',
        }

        def check(new):
            return common_check(new) and any(x == new.content for x in choices)

        try:
            result = await self.mousey.wait_for('message', check=check, timeout=60 * 5)
        except asyncio.TimeoutError:
            await ctx.send('Cancelled setup after inactivity.')
            return

        activity = choices[result.content]

        await ctx.send(
            inspect.cleandoc(
                f"""
                {prefix}Please specify which users to prune:

                `all`: Prune regardless of roles (ignores moderators)
                `no roles`: Only remove users having no roles
                Alternatively send role IDs/mentions of roles to include (ignores moderators)
                """
            )
        )

        choices = {
            'no roles': [],
            'all': [ctx.guild.id],
        }

        def check(new):
            return common_check(new) and (match_role_ids(new) or any(x == new.content for x in choices))

        try:
            result = await self.mousey.wait_for('message', check=check, timeout=60 * 5)
        except asyncio.TimeoutError:
            await ctx.send('Cancelled setup after inactivity.')
            return

        role_ids = choices.get(result.content) or match_role_ids(result)

        async with self.mousey.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO autoprune (guild_id, role_ids, activity_type, inactive_timeout)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id) DO UPDATE
                SET role_ids = EXCLUDED.role_ids, activity_type = EXCLUDED.activity_type,
                    inactive_timeout = EXCLUDED.inactive_timeout, updated_at = NOW()
                """,
                ctx.guild.id,
                role_ids,
                activity,
                datetime.timedelta(days=days),
            )

        await ctx.invoke(self.autoprune)

    @autoprune.command('remove')
    @bot_has_permissions(send_messages=True)
    async def autoprune_remove(self, ctx):
        """
        Remove an autoprune rule for the current server if it exists.

        Example: `{prefix}autoprune remove`
        """

        async with self.mousey.db.acquire() as conn:
            await conn.execute('DELETE FROM autoprune WHERE guild_id = $1', ctx.guild.id)

        await ctx.send('Removed all active autoprune rules.')

    @group()
    @bot_has_permissions(send_messages=True)
    async def permissions(self, ctx):
        """
        View current permissions settings.

        Example: `{prefix}permissions`
        """

        config = await self._get_config(ctx.guild)

        if not config.required_roles:
            roles = 'All users can use the bot'
        else:
            mentions = ' '.join(f'<@&{x}>' for x in config.required_roles)
            roles = f'Users with **one of** these roles can use the bot: {mentions}'

        message = inspect.cleandoc(
            f"""
            Permissions settings for {ctx.guild}:

            \N{BULLET} {roles}

            Additional settings will be added in the future.
            """
        )

        await ctx.send(message)

    @permissions.command('roles')
    @bot_has_permissions(send_messages=True)
    async def permissions_roles(self, ctx, *roles: discord.Role):
        """
        Define a set of roles which is allowed to use the bot.
        You may provide no roles to allow everyone to use the bot (default).

        Roles can be specified using their mention, ID, or name.

        Example: `{prefix}permissions roles`
        Example: `{prefix}permissions roles Luma "Blob Police"`
        """

        async with self.mousey.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guild_configs (guild_id, required_roles)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE
                SET required_roles = EXCLUDED.required_roles
                """,
                ctx.guild.id,
                [x.id for x in roles],
            )

        self.mousey.dispatch('mouse_config_update', ctx.guild)

        await asyncio.sleep(0)
        await ctx.invoke(self.permissions)

    @group(enabled=False)
    async def reload(self, ctx):
        pass

    @reload.command('config')
    @bot_has_permissions(send_messages=True)
    async def reload_config(self, ctx):
        """
        Force the config of the current server to reload.

        Example: `{prefix}reload`
        """

        self.mousey.dispatch('mouse_config_update', ctx.guild)
        await ctx.send('Reloaded the config for the current server.')

    @Plugin.listener()
    async def on_mouse_config_update(self, guild):
        try:
            del self._configs[guild.id]
        except KeyError:
            pass

    async def get_prefixes(self, guild):
        return (await self._get_config(guild)).prefixes

    async def _get_config(self, guild):
        try:
            return self._configs[guild.id]
        except KeyError:
            pass

        async with self.mousey.db.acquire() as conn:
            record = await conn.fetchrow(
                'SELECT prefixes, required_roles FROM guild_configs WHERE guild_id = $1', guild.id
            )

        if record is None:
            record = {}

        self._configs[guild.id] = config = GuildConfig(**record)
        return config
