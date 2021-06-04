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


class LogType(discord.Enum):
    # Bot created events

    BOT_INFO = 1 << 0
    COMMAND_USED = 1 << 1

    # Dispatched by Discord

    MEMBER_JOIN = 1 << 2
    MEMBER_REMOVE = 1 << 3

    MEMBER_SCREENING_COMPLETE = 1 << 23

    MEMBER_NAME_CHANGE = 1 << 4
    MEMBER_NICK_CHANGE = 1 << 5

    MEMBER_ROLE_ADD = 1 << 6
    MEMBER_ROLE_REMOVE = 1 << 7

    MEMBER_VOICE_JOIN = 1 << 8
    MEMBER_VOICE_MOVE = 1 << 9
    MEMBER_VOICE_REMOVE = 1 << 10

    MEMBER_KICK = 1 << 11
    MEMBER_BAN = 1 << 12
    MEMBER_UNBAN = 1 << 13

    ROLE_CREATE = 1 << 14
    ROLE_UPDATE = 1 << 15
    ROLE_DELETE = 1 << 16

    CHANNEL_CREATE = 1 << 17
    CHANNEL_UPDATE = 1 << 18
    CHANNEL_DELETE = 1 << 19

    MESSAGE_EDIT = 1 << 20
    MESSAGE_DELETE = 1 << 21
    MESSAGE_BULK_DELETE = 1 << 22

    # Infractions / Moderation Plugin

    MEMBER_WARN = 1 << 24
    MEMBER_NOTE_ADD = 1 << 25

    MEMBER_MUTE = 1 << 26
    MEMBER_UNMUTE = 1 << 27
