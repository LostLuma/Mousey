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
import logging
import typing

import discord
from discord.ext import tasks

from ... import Plugin
from .enums import ActivityType


log = logging.getLogger(__name__)

# Moderator permissions - ignore these users unconditionally
PERMISSIONS = discord.Permissions(administrator=True, ban_members=True, kick_members=True, manage_messages=True)


def has_no_roles(member):
    return len(member.roles) == 1


def has_any_role(role_ids):
    def check(member):
        return any(x.id in role_ids for x in member.roles)

    return check


def joined_before(config):
    now = datetime.datetime.utcnow()
    timeout = config.inactive_timeout.total_seconds()

    async def check(member):
        return (now - member.joined_at).total_seconds() >= timeout

    return check


def seen_before(config, mousey):
    now = datetime.datetime.utcnow()
    timeout = config.inactive_timeout.total_seconds()

    tracking = mousey.get_cog('Tracking')

    async def check(member):
        status = await tracking.get_last_status(member)

        # Default to rule setup date
        # To allow pruning members never seen
        return (now - status.seen or config.updated_at).total_seconds() >= timeout

    return check


def status_before(config, mousey):
    now = datetime.datetime.utcnow()
    timeout = config.inactive_timeout.total_seconds()

    tracking = mousey.get_cog('Tracking')

    async def check(member):
        status = await tracking.get_last_status(member)

        # Default to rule setup date
        # To allow pruning members never online or seen
        return (now - max(status.status, status.seen) or config.updated_at).total_seconds() >= timeout

    return check


class PruneConfig(typing.NamedTuple):
    guild_id: int
    role_ids: typing.List[int]

    activity_type: ActivityType
    inactive_timeout: datetime.timedelta

    updated_at: datetime.datetime


class AutoPrune(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self.do_prune.start()

    def cog_unload(self):
        self.do_prune.stop()

    @tasks.loop(hours=24)
    async def do_prune(self):
        await self.mousey.wait_until_ready()

        async with self.mousey.db.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT guild_id, role_ids, activity_type, inactive_timeout, updated_at
                FROM autoprune
                WHERE (guild_id >> 22) % $2 = $1
                """,
                self.mousey.shard_id,
                self.mousey.shard_count,
            )

        for record in records:
            data = dict(record)
            data['activity_type'] = ActivityType(data['activity_type'])

            config = PruneConfig(**data)
            await self._do_guild_prune(config)

    async def _do_guild_prune(self, config):
        guild = self.mousey.get_guild(config.guild_id)

        if not guild.me.guild_permissions.kick_members:
            return

        if not guild.chunked:
            await guild.chunk()

        if not config.role_ids:
            role_check = has_no_roles
        else:
            role_check = has_any_role(config.role_ids)

        if config.activity_type is ActivityType.joined:
            activity_check = joined_before(config)
        elif config.activity_type is ActivityType.seen:
            activity_check = seen_before(config, self.mousey)
        else:
            activity_check = status_before(config, self.mousey)

        me = guild.me
        events = self.mousey.get_cog('Events')

        for member in guild.members:
            if member.bot or member.top_role >= me.top_role:
                continue

            permissions = member.guild_permissions
            if permissions.value & PERMISSIONS.value != 0:  # Mod
                continue

            if role_check(member) and await activity_check(member):
                events.ignore(guild, 'member_kick', member)
                reason = 'Automatic prune due to inactivity'

                try:
                    await member.kick(reason=reason)
                except discord.HTTPException:
                    pass
                else:
                    self.mousey.dispatch('mouse_member_kick', member, me, reason)
