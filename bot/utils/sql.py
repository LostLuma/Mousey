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

PGSQL_ARG_LIMIT = 32767


def multirow_insert(items):
    """
    Creates a multirow insert query for the given iterable.

    Example:

    .. code-block :: python3
        params = list((x.id, x.bot, x.avatar, x.discriminator) for x in chunk)

        await conn.execute(
            f\"""
            INSERT INTO users (user_id, bot, avatar, discriminator)
            VALUES {multirow_insert(params)}
            ON CONFLICT (user_id) DO UPDATE
            SET avatar = EXCLUDED.avatar, discriminator = EXCLUDED.discriminator
            \""",
            *list(itertools.chain.from_iterable(params)),
        )

        # INSERT INTO x (user_id, bot, ...) VALUES ($1, $2, ...), ($5, $6, ...), ...

    Parameters
    ----------
    items : Iterable[Sequence[Any]]
        The objects passed to asyncpg, divided into sub-iterables per query.

    Returns
    -------
    str
        The query to insert all objects at once.
    """

    per = len(items[0])

    def row_insert(seq):
        return ', '.join(f'${x}' for x in range(per * seq + 1, per * (seq + 1) + 1))

    return ', '.join(f'({row_insert(x)})' for x in range(len(items)))
