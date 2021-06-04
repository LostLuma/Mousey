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
import typing

import discord
from discord.ext import commands

from ... import InfractionEvent, SafeUser, action_reason, bot_has_permissions
from ...utils import TimeConverter, describe_user


Users = commands.Greedy[SafeUser]
Time = typing.Optional[TimeConverter]


def maybe_describe(user):
    try:
        return describe_user(user)
    except AttributeError:
        return str(user.id)  # Unresolved user


async def _get_full_user(ctx, user):
    if isinstance(user, discord.abc.User):
        return user

    return ctx.bot.get_user(user.id) or await ctx.bot.fetch_user(user.id)


def wrap_mod_command_handler(*, can_expire, success_verb, event_name=None, user_converter=Users):
    def decorator(func):
        nonlocal event_name

        event_name = f'mouse_member_{event_name or func.__name__}'

        async def command_implementation(self, ctx, users, time, reason):
            succeeded = []

            missing_permissions = []
            bot_missing_permissions = []

            user_not_found = []
            http_exception = collections.defaultdict(list)

            events = self.mousey.get_cog('Events')

            for user in users:
                if isinstance(user, discord.Member):
                    if user.top_role >= ctx.author.top_role:
                        missing_permissions.append(user)
                        continue

                    if user.top_role >= ctx.guild.me.top_role:
                        bot_missing_permissions.append(user)
                        continue

                # This event might use an incomplete user, which is why it's re-created below
                events.ignore(ctx.guild, event_name, InfractionEvent(ctx.guild, user, ctx.author, reason))

                try:
                    await func(self, ctx, user, reason)
                except discord.NotFound:  # Executing eg. a ban will fail if the user is not valid
                    user_not_found.append(user)
                except discord.HTTPException as e:
                    http_exception[e.status, e.code, e.text].append(user)
                else:
                    try:
                        user = await _get_full_user(ctx, user)
                    except discord.NotFound:  # The mute command ignores non-members, so we catch invalid users here
                        user_not_found.append(user)
                        continue

                    succeeded.append(user)
                    self.mousey.dispatch(event_name, InfractionEvent(ctx.guild, user, ctx.author, reason))

            messages = []
            count = len(succeeded)

            if count > 1:
                messages.extend((f'Successfully {success_verb} {count} users.', ''))
            elif count == 1:
                messages.extend((f'Successfully {success_verb} `{describe_user(succeeded[0])}`.', ''))

            if user_not_found:
                messages.append(f'Invalid user IDs: ' + ' '.join(f'`{x.id}`' for x in user_not_found))

            if missing_permissions:
                users = [f'`{maybe_describe(x)}`' for x in missing_permissions]
                messages.append(f'Your top role is too low to action: ' + ' '.join(users))

            if bot_missing_permissions:
                users = [f'`{maybe_describe(x)}`' for x in bot_missing_permissions]
                messages.append(f'The bots top role is too low to action: ' + ' '.join(users))

            # I don't currently want to handle every failure state here,
            # So we'll just report back the API error to the user instead
            for (status, code, message), users in http_exception.items():
                users = [f'`{maybe_describe(x)}`' for x in users]
                messages.append('Failed to action users: ' + ' '.join(users) + f' (`{code}`: {message})')

            await ctx.send('\n'.join(messages))

        # fmt: off
        if not can_expire:
            @bot_has_permissions(send_messages=True)
            async def generated_command(self, ctx, users: user_converter, *, reason: action_reason = None):
                await command_implementation(self, ctx, users, None, reason)
        else:
            @bot_has_permissions(send_messages=True)
            async def generated_command(self, ctx, users: user_converter, time: Time, *, reason: action_reason = None):
                await command_implementation(self, ctx, users, time, reason)
        # fmt: on

        generated_command.__doc__ = func.__doc__
        generated_command.__name__ = func.__name__

        return generated_command

    return decorator
