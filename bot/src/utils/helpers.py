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

import inspect


# Thanks to Danny for posting this on the discord.py server
def populate_methods(source):
    def decorator(cls):
        for name, value in source.__dict__.items():
            if isinstance(value, staticmethod):
                setattr(cls, name, value)
            elif inspect.isfunction(value) and not name.startswith('_'):
                setattr(cls, name, value)
        return cls

    return decorator


async def ensure_user(connection, user):
    await connection.execute(
        """
        INSERT INTO users (id, bot, name, discriminator, avatar)
        VALUES  ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name, discriminator = EXCLUDED.discriminator, avatar = EXCLUDED.avatar
        """,
        user.id,
        user.bot,
        user.name,
        user.discriminator,
        user.avatar,
    )


def has_membership_screening(guild):
    return 'MEMBER_VERIFICATION_GATE_ENABLED' in guild.features
