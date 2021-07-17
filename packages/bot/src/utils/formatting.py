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

import unicodedata


def force_ltr(text):
    """Encapsulates a string to prevent RTL from messing up outside text."""

    text = str(text)

    required = any(unicodedata.bidirectional(x) in ('R', 'AL') for x in text)
    return f'\u2068{text}\u2069' if required else text


def remove_accents(text):
    """Replace grave accents with another character not used in Discord markdown."""

    return str(text).replace('\N{GRAVE ACCENT}', '\N{MODIFIER LETTER GRAVE ACCENT}')


def code_safe(text):
    """Shortcut to remove grave accents and encapsulate RTL text."""

    return remove_accents(force_ltr(text))


def user_name(user):
    """Converts to a safe representation of the users DiscordTag."""

    return f'{code_safe(user.name)}#{user.discriminator}'


def describe(item):
    """Turn a Discord object into a string representation, with ID if possible."""

    if not hasattr(item, 'id'):
        return code_safe(item)

    return f'{code_safe(item)} {item.id}'


def describe_user(user):
    """Converts a user to their text representation."""

    return f'{user_name(user)} {user.id}'


def join_parts(parts):
    if not parts:
        return ''

    return '\n' + '\n'.join(f'\N{BULLET} {x}' for x in parts)


# Copied from https://github.com/Rapptz/RoboDanny
class Plural:
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        singular, sep, plural = format_spec.partition('|')

        if abs(self.value) == 1:
            return f'{self.value} {singular}'

        plural = plural or f'{singular}s'
        return f'{self.value} {plural}'
