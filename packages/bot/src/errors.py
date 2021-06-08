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

from discord.ext import commands


class BannedUserNotFound(commands.BadArgument):
    def __init__(self, argument):
        self.argument = argument

        super().__init__(f'User "{argument}" is not banned or does not exist.')


class NoThreadChannels(commands.CheckFailure):
    def __init__(self):
        super().__init__('This command can only be used outside of thread channels.')


class VisibleCommandError(commands.CommandError):
    """A command error that can be raised and will directly be shown to the user."""

    pass
