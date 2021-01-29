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

import urllib.parse


def serialize_datetime(value):
    if value is not None:
        return value.isoformat()


def serialize_user(user):
    data = {
        'id': user.id,
        'bot': user.bot,
        'name': user.name,
        'discriminator': user.discriminator,
        'avatar': user.avatar,
    }

    return data


def attachment_paths(attachments):
    return [urllib.parse.urlparse(x.url).path for x in attachments]
