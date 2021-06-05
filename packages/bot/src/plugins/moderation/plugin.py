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
from discord.ext import commands

from ... import MemberRoleChangeEvent, Plugin, SafeBannedUser, bot_has_guild_permissions, command, group
from ...utils import describe, describe_user
from .checks import guild_has_mute_role
from .command import wrap_mod_command_handler


def default_reason(ctx, reason):
    return reason or f'Requested by {describe_user(ctx.author)}'


BannedUsers = commands.Greedy[SafeBannedUser]


class Moderation(Plugin):
    @command()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @wrap_mod_command_handler(can_expire=False, success_verb='warned')
    async def warn(self, ctx, user, reason):
        """
        Send an anonymous DM with the warning message to the specified users.

        Note that this command can only be used once concurrently per server,
        and warning DMs will only be sent for current server members to prevent abuse.

        Users must be specified as a mention, ID, or exact DiscordTag match.
        Reason must be any text less than 1000 characters in length.

        Example: `{prefix}warn LostLuma#7931 Disrupting chat by posting random emoji during conversations`
        """

        if not isinstance(user, discord.Member):
            return

        message = f'A warning was issued towards you in {describe(ctx.guild)}'

        if reason is None:
            message += '.'
        else:
            message += f':\n\n{reason}'

        try:
            await user.send(message)
        except discord.HTTPException:
            pass

    @command(aliases=['tempmute'])
    @commands.has_guild_permissions(manage_messages=True)
    @guild_has_mute_role()
    @bot_has_guild_permissions(manage_roles=True)
    @wrap_mod_command_handler(can_expire=False, success_verb='muted')
    # @wrap_mod_command_handler(can_expire=True, success_verb='muted')
    async def mute(self, ctx, user, reason):
        """
        Mute the specified users indefinitely or for a specified amount of time.

        Users must be specified as a mention, ID, or exact DiscordTag match.
        Reason can be any text less than 1000 characters in length.

        Example: `{prefix}mute LostLuma#7931 Continually disrupting conversations`
        Example: `{prefix}mute LostLuma#7931 2h Keeps posting pictures when users are chatting`
        """

        if not isinstance(user, discord.Member):
            return

        role = await self.get_mute_role(ctx.guild)

        if role in user.roles:
            return

        event = MemberRoleChangeEvent(user, role, ctx.author, reason)

        events = self.mousey.get_cog('Events')
        events.ignore(ctx.guild, 'mouse_role_add', event)

        await user.add_roles(role, reason=default_reason(ctx, reason))
        self.mousey.dispatch('mouse_role_add', event)

    @command()
    @commands.has_guild_permissions(manage_messages=True)
    @guild_has_mute_role()
    @bot_has_guild_permissions(manage_roles=True)
    @wrap_mod_command_handler(can_expire=False, success_verb='unmuted')
    async def unmute(self, ctx, user, reason):
        """
        Unmute the specified users.

        Users must be specified as a mention, ID, or exact DiscordTag match.
        Reason can be any text less than 1000 characters in length.

        Example: `{prefix}unmute LostLuma#7931 Appealed previous actions in modmail thread`
        """

        if not isinstance(user, discord.Member):
            return

        role = await self.get_mute_role(ctx.guild)

        if role not in user.roles:
            return

        event = MemberRoleChangeEvent(user, role, ctx.author, reason)

        events = self.mousey.get_cog('Events')
        events.ignore(ctx.guild, 'mouse_role_remove', event)

        await user.remove_roles(role, reason=default_reason(ctx, reason))
        self.mousey.dispatch('mouse_role_remove', event)

    @command()
    @commands.check_any(
        commands.has_guild_permissions(kick_members=True), commands.has_guild_permissions(ban_members=True)
    )
    @bot_has_guild_permissions(kick_members=True)
    @wrap_mod_command_handler(can_expire=False, success_verb='kicked')
    async def kick(self, ctx, user, reason):
        """
        Kick the specified users from the server.

        Users must be specified as a mention, ID, or exact DiscordTag match.
        Reason can be any text less than 1000 characters in length.

        Example: `{prefix}kick LostLuma#7931 Refusing to remove inappropriate custom status`
        """

        await ctx.guild.kick(user, reason=default_reason(ctx, reason))

    @group(aliases=['tempban'])
    @commands.has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    @wrap_mod_command_handler(can_expire=False, success_verb='banned')
    # @wrap_mod_command_handler(can_expire=True, success_verb='banned')
    async def ban(self, ctx, user, reason):
        """
        Ban the specified users indefinitely or for a specified amount of time.
        You may specify the `--keep` flag in order to preserve messages of banned users.

        Users must be specified as a mention, ID, or exact DiscordTag match.
        Reason can be any text less than 1000 characters in length.

        Example: `{prefix}ban LostLuma#7931 Spamming unwholesome images in #general`
        Example: `{prefix}ban --keep LostLuma#7931 1w Needs some time away, see previous infractions`
        """

        await ctx.guild.ban(user, delete_message_days=1, reason=default_reason(ctx, reason))

    @ban.command('--keep', hidden=True, help=ban.help)
    @commands.has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    @wrap_mod_command_handler(can_expire=False, success_verb='banned', event_name='ban')
    # @wrap_mod_command_handler(can_expire=True, success_verb='banned', event_name='ban')
    async def ban_keep(self, ctx, user, reason):
        await ctx.guild.ban(user, delete_message_days=0, reason=default_reason(ctx, reason))

    @command()
    @commands.has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    @wrap_mod_command_handler(can_expire=False, success_verb='unbanned', user_converter=BannedUsers)
    async def unban(self, ctx, user, reason):
        """
        Unban the specified users.

        Users must be specified as a mention, ID, or exact DiscordTag match.
          Note: The specified users must be banned from the server.
        Reason can be any text less than 1000 characters in length.

        Example: `{prefix}unban LostLuma#7931 Appealed via DMs https://files.lostluma.dev/nzyJl5.jpg`
        """

        await ctx.guild.unban(user, reason=default_reason(ctx, reason))

    async def get_mute_role(self, guild):
        # TODO: Mute role should be configurable per server

        names = ('mute', 'muted')
        return discord.utils.find(lambda x: x.name.lower() in names, guild.roles)
