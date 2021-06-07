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

import collections
import datetime
import inspect
import io

import discord
from discord.ext import commands

from ... import Plugin, VisibleCommandError, bot_has_guild_permissions, bot_has_permissions, command, emoji, group
from ...utils import Plural, has_membership_screening, human_delta
from .converter import MentionableRole, info_category


VALID_GUILD_CATEGORIES = ('general', 'moderation', 'counts', 'premium')

PREMIUM_GUILD_EMOJI = {
    0: emoji.PREMIUM_GUILD_TIER_0,
    1: emoji.PREMIUM_GUILD_TIER_1,
    2: emoji.PREMIUM_GUILD_TIER_2,
    3: emoji.PREMIUM_GUILD_TIER_3,
}

CHANNEL_EMOJI = {
    discord.ChannelType.text: emoji.TEXT_CHANNEL,
    discord.ChannelType.voice: emoji.VOICE_CHANNEL,
    discord.ChannelType.category: emoji.CATEGORY_CHANNEL,
    discord.ChannelType.news: emoji.NEWS_CHANNEL,
    discord.ChannelType.store: emoji.STORE_CHANNEL,
}


# user, role, invite, etc. info
class Utility(Plugin):
    @command()
    @bot_has_permissions(attach_files=True, embed_links=True, send_messages=True)
    async def avatar(self, ctx, *, user: discord.User = None):
        """
        Shows the current avatar of a user.

        User can be specified as a mention, ID, DiscordTag, name, or will default to the author.

        Example: `{prefix}avatar Mousey#4545`
        """

        user = user or ctx.author

        avatar_url = user.avatar.with_static_format('png').url
        avatar_ext = 'gif' if user.avatar.is_animated() else 'png'

        # Send as attachment if possible, as URLs expire
        file = None
        content = None

        async with self.mousey.session.get(avatar_url) as resp:
            size = int(resp.headers['Content-Length'])

            if size <= ctx.guild.filesize_limit:
                data = io.BytesIO(await resp.read())
                file = discord.File(data, 'avatar.' + avatar_ext)

        if file is None:
            content = avatar_url

        await ctx.send(content, file=file)

    @command()
    @bot_has_permissions(send_messages=True)
    async def joined(self, ctx, *, user: discord.Member = None):
        """
        Shows when a member joined the current server and Discord.

        User can be specified as a mention, ID, DiscordTag, name or will default to the author.

        Example: `{prefix}joined LostLuma#7931`
        """

        user = user or ctx.author
        now = discord.utils.utcnow()

        await ctx.send(
            f'{user} joined this server `{human_delta(now - user.joined_at)}` '
            f'ago, they joined Discord `{human_delta(now - user.created_at)}` ago.'
        )

    @command()
    @bot_has_permissions(send_messages=True)
    async def seen(self, ctx, *, user: discord.Member = None):
        """
        Shows when a member was last seen and sent their last message.

        User can be specified as a mention, ID, DiscordTag, name or will default to the author.

        Example: `{prefix}seen LostLuma#7931`
        """

        user = user or ctx.author

        now = datetime.datetime.utcnow()
        status = await self.mousey.get_cog('Tracking').get_last_status(user)

        if status.status is None:
            presence = f'has not been seen online'
        else:
            prefix = 'on ' if user.status is discord.Status.dnd else ''
            presence = f'has been {prefix}{user.status} for `{human_delta(now - status.status)}`'

        if status.seen is None:
            seen = ''
        else:
            seen = f', they were last seen `{human_delta(now - status.seen)}` ago'

        if status.spoke is None:
            spoke = ', and has not been seen speaking'
        else:
            spoke = f', and last spoke `{human_delta(now - status.spoke)}` ago'

        await ctx.send(f'{user} {presence}{seen}{spoke}.')

    @group(invoke_without_command=False, hidden=True)
    @commands.cooldown(2, 60, commands.BucketType.guild)
    async def mention(self, ctx):
        """Please see the mention sub commands for help instead."""

        pass  # TODO: Create decorator to share cooldowns properly

    @mention.command('role')
    @commands.check_any(
        commands.has_permissions(mention_everyone=True), commands.has_guild_permissions(manage_roles=True)
    )
    @bot_has_permissions(send_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def mention_role(self, ctx, roles: commands.Greedy[MentionableRole], *, message: str = None):
        """
        Mention one or more roles in the current channel with an optional message.
        Your command invocation message will be deleted if the command was successful.

        For moderators without @everyone permissions this is useful to not need to edit roles manually.

        Roles must be specified as a mention, ID, or name.
        Message can be any message, or empty to only mention the roles.

        Example: `{prefix}mention role Luma Hello! ...`
        Example: `{prefix}mention role "LF Campaign" "LF Pathfinder"`
        """

        edited = []
        reason = f'Requested by {ctx.author}'

        def not_mentionable(x):
            return not x.mentionable

        try:
            if not ctx.guild.me.guild_permissions.mention_everyone:
                for role in filter(not_mentionable, ctx.guild.roles):
                    edited.append(role)
                    await role.edit(mentionable=True, reason=reason)

            mentions = ' '.join(x.mention for x in roles)
            allowed_mentions = discord.AllowedMentions(roles=set(roles))

            await self._mention_command(ctx, mentions, message, allowed_mentions)
        finally:
            for role in edited:
                await role.edit(mentionable=False, reason=reason)

    @mention.command('everyone', aliases=['here'])
    @commands.has_permissions(mention_everyone=True)
    @bot_has_permissions(send_messages=True, mention_everyone=True)
    async def mention_everyone(self, ctx, *, message: str = None):
        """
        Mention @everyone or @here in the current channel with an optional message.
        Your command invocation message will be deleted if the command was successful.

        Message can be any message, or empty to only mention the target.

        Example: `{prefix}mention here`
        Example: `{prefix}mention everyone beep boop`
        """

        mentions = f'@{ctx.invoked_with}'
        allowed_mentions = discord.AllowedMentions(everyone=True)

        await self._mention_command(ctx, mentions, message, allowed_mentions)

    @mention.command('user', hidden=True)
    @commands.has_permissions(manage_messages=True)
    @bot_has_permissions(send_messages=True)
    async def mention_user(self, ctx, users: commands.Greedy[discord.User], *, message: str = None):
        """
        Mention one or more users in the current channel with an optional message.
        Your command invocation message will be deleted if the command was successful.

        Message can be any message, or empty to only mention the target.

        Example: `{prefix}mention user LostLuma#7931 Hello, Luma!`
        """

        if len(users) > 12:
            raise VisibleCommandError('Can only mention up to 12 users per invocation.')

        mentions = ' '.join(x.mention for x in users)
        allowed_mentions = discord.AllowedMentions(users=set(users))

        await self._mention_command(ctx, mentions, message, allowed_mentions)

    async def _mention_command(self, ctx, mentions, message, allowed_mentions):
        message = message or ''
        await ctx.send(f'{mentions} {message}', allowed_mentions=allowed_mentions)

        if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.message.delete()

    @command(aliases=['serverinfo'])
    @bot_has_permissions(embed_links=True, send_messages=True, use_external_emojis=True)
    async def server(self, ctx, *, category: info_category(VALID_GUILD_CATEGORIES) = None):
        """
        Shows detailed information about the current server.

        Category can be one of `general`, `moderation`, `counts`, `premium` to show specific details ony.

        Example: `{prefix}server`
        Example: `{prefix}server counts`
        """

        guild = ctx.guild
        # Some properties are only set fetched with counts:
        # approximate_member_count, approximate_presence_count, max_members

        # TODO: Use proper fetch_guild call once attributes are implemented
        params = {'with_counts': 1}
        route = discord.http.Route('GET', '/guilds/{guild_id}', guild_id=ctx.guild.id)

        fetched = await self.mousey.http.request(route, params=params)

        embed = discord.Embed()

        if guild.icon is not None:
            embed.set_thumbnail(url=guild.icon.url)

        embed.description = guild.description
        embed.title = f'Server Information - {guild.name}'

        if category:
            categories = [category]
        else:
            categories = VALID_GUILD_CATEGORIES

        for name in categories:
            method = getattr(self, f'_add_{name}_guild_field')
            method(embed, guild, fetched)  # Embed is modified in-place

        await ctx.send(embed=embed)

    def _add_general_guild_field(self, embed, guild, fetched):
        created_at = guild.created_at.strftime('%Y-%m-%d %H:%M')

        programs = []

        if 'PARTNERED' in guild.features:
            programs.append('Discord Partner')
        if 'VERIFIED' in guild.features:
            programs.append('Verified Server')

        programs = '**Programs:** ' + '; '.join(programs) + '\n' if programs else ''

        if not guild.features:
            features = ''
        else:
            features = '**Features:** ' + ', '.join(f'`{x}`' for x in sorted(guild.features))

        general = inspect.cleandoc(
            f"""
            **ID:** `{guild.id}`
            **Created:** `{created_at}`

            **Locale:** `{guild.preferred_locale}`
            **Region:** `{guild.region}`
            """
        )

        embed.add_field(name='General', value=general + '\n\n' + programs + features, inline=False)

    def _add_moderation_guild_field(self, embed, guild, fetched):
        mfa_status = 'Requires 2FA' if guild.mfa_level else 'No 2FA required'

        if guild.default_notifications is discord.NotificationLevel.all_messages:
            default_notifications = 'All Messages'
        else:
            default_notifications = 'Mentions Only'

        if guild.explicit_content_filter is discord.ContentFilter.disabled:
            content_filter = 'Disabled'
        elif guild.explicit_content_filter is discord.ContentFilter.all_members:
            content_filter = 'Enabled for everyone'
        else:
            content_filter = 'Enabled for users without roles'

        verification_level = str(guild.verification_level).replace('extreme', 'highest').title()

        embed.add_field(
            name='Moderation',
            value=inspect.cleandoc(
                f"""
                **MFA Status:** {mfa_status}
                **Default Notifications:** {default_notifications}

                **Content Filter:** {content_filter}
                **Verification Level:** {verification_level}
                """
            ),
            inline=False,
        )

    def _add_counts_guild_field(self, embed, guild, fetched):
        bot_count = sum(x.bot for x in guild.members)

        if not has_membership_screening(guild):
            pending = ''
        else:
            pending = f'; {sum(x.pending for x in guild.members):,} pending'

        presences = collections.Counter(x.status for x in guild.members)

        online = f'{emoji.ONLINE} {presences[discord.Status.online]:,}'
        idle = f'{emoji.IDLE} {presences[discord.Status.idle]:,}'
        dnd = f'{emoji.DND} {presences[discord.Status.dnd]:,}'

        active = fetched['approximate_presence_count']
        inactive = guild.member_count - fetched['approximate_presence_count']

        role_count = len(guild.roles)

        integrated_role_count = sum(x.tags is not None for x in guild.roles)
        integrated_roles = f'({integrated_role_count} integrated) ' if integrated_role_count else ''

        def not_managed(x):
            return not x.managed

        limit = guild.emoji_limit

        static_count = sum(not x.animated for x in filter(not_managed, guild.emojis))
        animated_count = sum(x.animated for x in filter(not_managed, guild.emojis))

        managed_count = sum(x.managed for x in guild.emojis)  # Synced via Twitch etc.
        managed_emoji = f'; {managed_count} external' if managed_count else ''

        channels = collections.Counter(x.type for x in guild.channels)

        def channel_symbol(channel_type):
            return CHANNEL_EMOJI.get(channel_type, channel_type.name)

        channel_count = sum(channels.values())
        channels = ' '.join(f'{channel_symbol(channel_type)} {count}' for channel_type, count in channels.items())

        embed.add_field(
            name='Counts',
            value=inspect.cleandoc(
                f"""
                **Members:** {guild.member_count:,} ({Plural(bot_count):bot}{pending}) / {fetched['max_members']:,}

                **Statuses:** {online} {idle} {dnd}
                **Presences:** {active:,} active; {inactive:,} inactive

                **Roles:** {role_count} {integrated_roles}/ 250
                **Emoji:** {static_count} / {limit} static; {animated_count} / {limit} animated{managed_emoji}
                **Channels:** {channels} - {channel_count:,}  / 500
                """
            ),
            inline=False,
        )

    def _add_premium_guild_field(self, embed, guild, fetched):
        tier_emoji = PREMIUM_GUILD_EMOJI.get(guild.premium_tier, '')

        if not guild.premium_tier:
            perks = 'No current perks'
        else:
            bitrate = int(guild.bitrate_limit / 1000)
            filesize = int(guild.filesize_limit / 1024 ** 2)

            perks = [f'Bitrate: {bitrate} kbps', f'Emoji: {guild.emoji_limit}', f'Files: {filesize} MiB']

            if guild.premium_tier >= 1:
                perks.extend(['Animated Icon', 'Invite Background'])
            if guild.premium_tier >= 2:
                perks.extend(['Server Banner', '1080p Livestreams'])
            if guild.premium_tier >= 3:
                perks.extend(['Vanity URL'])

            perks = '; '.join(perks)

        embed.add_field(
            name='Premium',
            value=inspect.cleandoc(
                f"""
                **Boosts:** {emoji.PREMIUM_GUILD_ICON} {guild.premium_subscription_count:,}
                **Unique Boosters:** {len(guild.premium_subscribers):,}

                **Server Level:** {tier_emoji} Tier {guild.premium_tier}
                **Perks:** {perks}
                """
            ),
            inline=False,
        )
