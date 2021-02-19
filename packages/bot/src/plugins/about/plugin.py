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
import math
import time
import urllib.parse

import discord
from discord.ext import commands, tasks

from ... import HTTPException, Plugin, bot_has_permissions, command
from ...utils import Plural, describe
from .channel import RawChannelHelper
from .converter import ClientID
from .formatting import simple_link_escape


log = logging.getLogger(__name__)


GUILD_FEED = 298542293135392768
ANNOUNCEMENTS = 445054928679993355


def json_float(value):
    # json.loads refuses to load nan or inf
    if not (math.isnan(value) or math.isinf(value)):
        return value


def is_special(guild):
    """bool: Whether a guild is verified or partnered."""

    special = {'PARTNERED', 'VERIFIED'}

    # Test if any of the special features are present
    return not set(guild.features).isdisjoint(special)


def is_old_application(client_id):
    """bool: Whether an application may have a bot with a different user ID."""

    date = datetime.datetime(2016, 8, 1)
    return discord.utils.snowflake_time(client_id) < date


def oauth_url(client_id, guild=None, permissions=None, scopes=None):
    """str: Oauth2 authorization URL for the given bot."""

    params = {'client_id': client_id}

    if guild is not None:
        params['guild_id'] = guild.id

    if permissions is not None:
        params['permissions'] = permissions.value

    if scopes is not None:
        params['scope'] = scopes

    return 'https://discord.com/api/oauth2/authorize?' + urllib.parse.urlencode(params)


class About(Plugin):
    def __init__(self, mousey):
        super().__init__(mousey)

        self.update_status.start()
        self.update_status.add_exception_type(HTTPException)

    def cog_unload(self):
        self.update_status.cancel()

    @command(aliases=['github'])
    @bot_has_permissions(send_messages=True)
    async def source(self, ctx):
        """Displays a link to my source code on GitHub."""

        await ctx.send('You can find my source code here: <https://github.com/SnowyLuma/Mousey>')

    @command()
    @commands.has_permissions(manage_guild=True)
    @bot_has_permissions(send_messages=True, manage_webhooks=True)
    async def subscribe(self, ctx):
        """
        Subscribe the current channel to Mousey's announcement channel.

        Example: `{prefix}subscribe`
        """

        # noinspection PyProtectedMember
        news = RawChannelHelper(ANNOUNCEMENTS, self.mousey._connection)
        await news.follow(destination=ctx.channel, reason=f'Requested by {ctx.author}')

    @command(aliases=['ginv', 'inv'])
    @bot_has_permissions(send_messages=True)
    async def invite(self, ctx, *client_ids: ClientID):
        """
        Generates Mousey's or another application's oauth2 invite link.
        For interaction-only applications the bot scope will not be requested.

        Client IDs must be supplied as a mention, ID, or exact Name#Discriminator match.
          Note: For bots created after 2016-08-01 this is the same as the bot's user ID.

        Example: `{prefix}invite @Mousey#4545`
        """

        urls = []

        if client_ids:
            for client_id in client_ids:
                # If no bot user exists the oauth prompt would error given the bot scope
                user = None

                try:
                    user = self.mousey.get_user(client_id) or await self.mousey.fetch_user(client_id)
                except discord.NotFound:
                    if is_old_application(client_id):  # Assume all old applications will have bots
                        user = object()

                if user is None:
                    scopes = 'applications.commands'
                else:
                    scopes = 'applications.commands bot'

                urls.append(oauth_url(client_id, guild=ctx.guild, scopes=scopes))
        else:
            permissions = discord.Permissions(
                kick_members=True,
                ban_members=True,
                manage_channels=True,
                manage_guild=True,
                add_reactions=True,
                view_audit_log=True,
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                use_external_emojis=True,
                connect=True,
                mute_members=True,
                move_members=True,
                manage_nicknames=True,
                manage_roles=True,
                manage_webhooks=True,
            )

            scopes = 'applications.commands bot'
            urls.append(oauth_url(self.mousey.user.id, permissions=permissions, scopes=scopes))

        await ctx.send(f'\n'.join(f'<{url}>' for url in urls))

    @command(aliases=['rtt'])
    @bot_has_permissions(send_messages=True)
    async def ping(self, ctx):
        """
        Measures how long it takes the bot to send a message and shows WebSocket latency.

        Example: `{prefix}rtt`
        """

        start = time.perf_counter()
        msg = await ctx.send('...')

        duration = time.perf_counter() - start
        await msg.edit(content=f'Boop! rtt: {duration * 1000:.3f}ms; ws: {self.mousey.latency * 1000:.3f}ms')

    @Plugin.listener()
    async def on_mouse_guild_join(self, guild):
        log.info(f'Joined guild {guild!r}.')

        bots = sum(x.bot for x in guild.members)
        emoji = '\N{LARGE PURPLE CIRCLE}' if is_special(guild) else '\N{LARGE BLUE CIRCLE}'

        await self._log_guild_change(
            # As there are always at least two members we don't need to use Plural here
            f'{emoji} {describe(guild)} - {guild.member_count} members - {Plural(bots):bot} - {describe(guild.owner)}'
        )

    @Plugin.listener()
    async def on_mouse_guild_remove(self, guild):
        log.info(f'Left guild {guild!r}.')
        await self._log_guild_change(f'\N{LARGE RED CIRCLE} {describe(guild)}')

    async def _log_guild_change(self, content):
        for transform in (simple_link_escape, discord.utils.escape_markdown):
            content = transform(content)

        allowed_mentions = discord.AllowedMentions.none().to_dict()

        # Using the channel helper doesn't work with this,
        # As Messageable.send still uses State.get_channel
        try:
            await self.mousey.http.send_message(GUILD_FEED, content, allowed_mentions=allowed_mentions)
        except discord.HTTPException:
            pass

    @tasks.loop(minutes=1)
    async def update_status(self):
        shard_id = self.mousey.shard_id
        status = {'ready': self.mousey.is_ready(), 'latency': json_float(self.mousey.latency)}

        await self.mousey.api.set_status(shard_id, status)
