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

import discord
import jishaku.paginators

from .asyncio import create_task


class PaginatorInterface(jishaku.paginators.PaginatorInterface):
    @property
    def send_kwargs(self):
        count = self.page_count
        index = self.display_page

        page_num = f' - Page {index + 1}/{count}'
        return {'content': self.pages[index] + page_num}


async def _close_interface_context(ctx, interface):
    await interface.task

    # CancelledError or TimeoutError etc.
    if interface.close_exception is not None:
        return

    # Ensure permissions did not change while waiting
    if not ctx.channel.permissions_for(ctx.me).manage_messages:
        return

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


def close_interface_context(ctx, interface):
    """Removes invocation message when stop button is used."""

    if ctx.channel.permissions_for(ctx.me).manage_messages:
        create_task(_close_interface_context(ctx, interface))
