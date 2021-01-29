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
import re

from discord.ext import commands


# There is probably a lot of room for improvement here, but this works for now ..!

SECOND = 1
MINUTE = SECOND * 60
HOUR = MINUTE * 60
DAY = HOUR * 24
WEEK = DAY * 7
MONTH = DAY * 30
YEAR = DAY * 365


DURATIONS = {
    'y': YEAR,
    'year': YEAR,
    'years': YEAR,
    'mo': MONTH,
    'month': MONTH,
    'months': MONTH,
    'w': WEEK,
    'week': WEEK,
    'weeks': WEEK,
    'd': DAY,
    'day': DAY,
    'days': DAY,
    'h': HOUR,
    'hr': HOUR,
    'hour': HOUR,
    'hours': HOUR,
    'm': MINUTE,
    'min': MINUTE,
    'minute': MINUTE,
    'minutes': MINUTE,
    's': SECOND,
    'sec': SECOND,
    'second': SECOND,
    'seconds': SECOND,
}


def human_delta(interval):
    if isinstance(interval, float):
        interval = int(interval)
    elif isinstance(interval, datetime.timedelta):
        interval = int(interval.total_seconds())

    # TODO: Add months to the output
    # I'm skipping this to save some time for now
    years, rest = divmod(interval, YEAR)
    days, rest = divmod(rest, DAY)
    hours, rest = divmod(rest, HOUR)
    minutes, seconds = divmod(rest, MINUTE)

    periods = [(years, 'y'), (days, 'd'), (hours, 'h'), (minutes, 'm'), (seconds, 's')]
    periods = list(filter(lambda x: x[0] > 0, periods))  # Don't add empty periods to output

    def to_text(data):
        return ''.join(map(str, data))

    return ' and '.join(map(to_text, periods[0:2])) or '0s'


class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        view = ctx.view

        # Attempt to parse a date (eg. 2021-02-3)
        match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', argument)

        if match is not None:
            results = list(match.groups())

            if view.eof:
                match = None
                extra = None
            else:
                index = view.index

                view.skip_ws()
                extra = view.get_quoted_word()

                # Parse an hour and optional minute, if it exists
                match = re.match(r'(\d{1,2})?(?::(\d{1,2}))', extra)

                if match is None:
                    view.index = index
                else:
                    results.extend(match.groups())

            now = datetime.datetime.utcnow()
            moment = datetime.datetime(*map(int, results))

            if now < moment:
                return moment

            argument = argument + ' ' + extra if match else argument
            raise commands.BadArgument(f'Date "{argument}" is in the past.')

        original = view.index, view.previous

        # Attempt to parse one or more durations
        # This is supposed to behave like Greedy[...], except it's in the converter!
        total = 0
        view.index -= len(argument)

        while not view.eof:
            index = view.index

            view.skip_ws()
            argument = view.get_quoted_word()

            if argument.isdigit():  # Need another word for the unit
                view.skip_ws()
                argument += ' ' + view.get_quoted_word()

            match = re.match(r'^(\d+) ?([a-zA-Z]+)', argument, re.IGNORECASE)

            if match is None:
                value, unit = None, None
            else:
                value, unit = match.groups()
                # Revert back if multiple units, like "2h30m"
                view.index -= len(argument) - match.span()[1]

            if unit and unit.lower() in DURATIONS:
                total += DURATIONS[unit.lower()] * int(value)
            elif total > 0:  # Parsed duration from previous word(s)
                view.index = index
                break
            else:
                view.index, view.previous = original  # Reset view in case we're an optional argument
                raise commands.BadArgument(f'Can not convert "{argument}" to duration or timestamp.')

        return datetime.timedelta(seconds=total)
