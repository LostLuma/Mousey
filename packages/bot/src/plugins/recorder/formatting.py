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
import textwrap

from ...utils import code_safe


FORMATTING_RE = re.compile(
    r'(?P<markdown>[*_~`\\|])|'
    r'(?P<emoji><a?:\w{2,32}:\d{15,21}>)|'
    r'([\\<]+)?(?P<url>(?:https?|steam)://[^\s*~`|>]+)([\\>])?',
    re.IGNORECASE,
)


def describe_emoji(emoji):
    return f':{emoji.name}: {emoji.id}'


def join_with_code(words):
    return ', '.join(f'`{code_safe(x)}`' for x in words)


def join_parts(parts):
    if not parts:
        return ''

    return '\n' + '\n'.join(f'\N{BULLET} {x}' for x in parts)


def indent_multiline(text):
    if '\n' not in text:
        return text

    return '\n' + textwrap.indent(text, ' ' * 2)


def escape_formatting(text):
    def replace(match):
        emoji = match.group('emoji')

        if emoji is not None:
            return emoji

        markdown = match.group('markdown')

        if markdown is not None:
            return f'\\{markdown}'

        def escape_group(idx):
            return re.sub(r'([\\<>])', r'\\\1', match.group(idx) or '')

        url = match.group('url')
        return f'{escape_group(3)}<{url}>{escape_group(5)}'

    return FORMATTING_RE.sub(replace, text)
