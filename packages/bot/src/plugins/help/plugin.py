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

import collections
import inspect
import itertools
import re

from discord.ext import commands

from ... import Plugin, bot_has_permissions
from ... import command as command_
from ...utils import code_safe
from .converter import CommandConverter


NOTE = 'Need additional help? Join the Mousey Discord: <https://discord.gg/Yu5e7JG>'


class Help(Plugin):
    # @command_()  # TODO
    # @bot_has_permissions(send_messages=True)
    # async def prefix(self, ctx):
    #     """
    #     Shows all enabled command prefixes on the current server.
    #     Mentioning the bot will always work, regardless of custom prefixes being set.
    #
    #     Usage: `{prefix}prefix`
    #     """
    #
    #    ...

    @command_(aliases=['commands'])
    @bot_has_permissions(send_messages=True)
    async def help(self, ctx, *, command: CommandConverter = None):
        """
        Shows all commands you can use or information about a specific command.

        To specify a command simply use it's full name or any of it's aliases.

        Example: `{prefix}help invite`
        """

        if command is None:
            await self._general_help(ctx)
        else:
            await self._command_help(ctx, command)

    def clean_prefix(self, prefix):
        # Replace emoji and mentions with their rendered counterparts
        # Otherwise users are shown the raw form due to the code block

        prefix = re.sub(r'<a?:([\w-]{2,32}):\d{15,21}>', ':\\1:', prefix)  # Emoji
        prefix = re.sub(fr'<@!?{self.mousey.user.id}>', f'@{self.mousey.user} ', prefix)  # Mentions

        return code_safe(prefix)

    async def _general_help(self, ctx):
        categories = collections.defaultdict(list)

        for command in itertools.chain.from_iterable(x.walk_commands() for x in self.mousey.cogs.values()):
            if not command.enabled or any(x.hidden for x in (command, *command.parents)):
                continue

            try:
                if not await command.can_run(ctx):
                    continue
            except commands.CommandError:
                continue

            categories[command.cog_name].append(command)

        def fmt_commands(name):
            return ', '.join(f'`{x.qualified_name}`' for x in sorted(categories[name], key=lambda x: x.qualified_name))

        usable = '\n'.join(f'**{name}:** {fmt_commands(name)}' for name in sorted(categories))

        msg = inspect.cleandoc(
            """
            Your current permissions allow you to use the following commands:

            {commands}

            Use `{prefix}help <command>` for more information on each command.
            {note}
            """
        )

        await ctx.send(msg.format(commands=usable, prefix=self.clean_prefix(ctx.prefix), note=NOTE))

    async def _command_help(self, ctx, command):
        prefix = self.clean_prefix(ctx.prefix)
        name = f'{command.full_parent_name} {command.name}'.lstrip()

        if not command.signature:
            signature = ''
        else:
            signature = f' {command.signature}'

        try:
            can_run = await command.can_run(ctx)
        except commands.CommandError:
            can_run = False

        perms = '' if can_run else 'do not '
        description = command.help.replace('{prefix}', prefix) + '\n' if command.help is not None else ''

        msg = inspect.cleandoc(
            """
            Usage: `{prefix}{name}{signature}`
            You currently {perms}have the required permissions to run this command.

            {description}{note}
            """
        )

        await ctx.send(
            msg.format(prefix=prefix, name=name, signature=signature, perms=perms, description=description, note=NOTE)
        )
