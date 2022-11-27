# -*- coding: utf-8 -*-

"""
Mousey: Discord Moderation Bot
Copyright (C) 2016 - 2022 Lilly Rose Berner

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

from typing import TypedDict

import discord

from ... import BLOBS_GG_TOKEN, Plugin


GUILD_ID = 272885620769161216
BASE_URL = 'https://api.blobs.gg/v1'


class User(TypedDict):
    username: str
    discriminator: str
    avatar: str | None


class Blobs(Plugin):
    """Integration with the blobs.gg API."""

    @property
    def guild(self) -> discord.Guild | None:
        return self.mousey.get_guild(GUILD_ID)

    # Update existing users within the blobs.gg API
    # Ensures names and avatars are updated on drawfest pages

    @Plugin.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id == GUILD_ID:
            await self._update_user(member)

    @Plugin.listener()
    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        if self.guild is None:
            return

        member = self.guild.get_member(before.id)

        if member is not None:
            await self._update_user(member)

    async def _update_user(self, user: discord.Member) -> None:
        if BLOBS_GG_TOKEN is None:
            return

        headers: dict[str, str] = {
            'Authorization': BLOBS_GG_TOKEN,
        }

        data: User = {
            'username': user.name,
            'discriminator': user.discriminator,
            'avatar': user.avatar.key if user.avatar else None,
        }

        await self.mousey.session.patch(f'{BASE_URL}/users/{user.id}', json=data, headers=headers)
