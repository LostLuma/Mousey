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

import json

import cryptography.fernet

from ... import FERNET_KEY


_FERNET = cryptography.fernet.Fernet(FERNET_KEY)


def encrypt(data):
    return _FERNET.encrypt(data.encode('utf-8'))


def decrypt(data):
    return _FERNET.decrypt(data).decode('utf-8')


def encrypt_json(data):
    return encrypt(json.dumps(data))


def decrypt_json(data):
    return json.loads(decrypt(data))
