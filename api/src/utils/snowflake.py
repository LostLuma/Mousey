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

import os
import time


_generated_ids = 0


DISCORD_EPOCH = 1420070400000
SHIFTED_PID = os.getpid() << 12


# Thanks to luna (https://gitlab.com/luna) for providing a reference implementation
def generate_snowflake(worker_id=0):
    """
    Generate a Discord-like Snowflake for the current time.

    Parameters
    ----------
    worker_id: int
        The worker ID for the current process type (eg. shard ID, queue ID, ..).

    Returns
    -------
    int
        The generated snowflake.
    """

    global _generated_ids

    _generated_ids += 1
    generated = _generated_ids % 4096

    # Every process generating snowflakes should have a unique worker ID,
    # To prevent generating any duplicate snowflakes (even if this is unlikely)
    worker_id = worker_id << 17

    # Discord snowflakes start 2015-01-01
    # Use the same starting point so age is easy to tell
    snowflake = int(time.time() * 1000) - DISCORD_EPOCH << 22

    # 42 bits time, 5 worker, 5 process, 12 generated IDs
    return snowflake | worker_id | SHIFTED_PID | generated
