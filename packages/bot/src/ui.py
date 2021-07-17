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

__all__ = ('CancellableMenu', 'disable_when_pressed', 'ExitableMenu', 'Menu')

import asyncio
import contextlib
import functools

import discord

from .utils import create_task
from .view import View


MENU_TIMEOUT = 300


def _can_be_disabled(item):
    return hasattr(item, 'disabled')


def disable_when_pressed(func):
    @functools.wraps(func)
    async def callback_wrapper(self, component, interaction):
        async with self.disable(interaction=interaction):
            await func(self, component, interaction)

    return callback_wrapper


class Menu(View):
    def __init__(self, *, context):
        super().__init__(timeout=MENU_TIMEOUT)

        self.message = None
        self.context = context

        self._disabled = False

    @property
    def mousey(self):
        return self.context.bot

    @property
    def guild(self):
        return self.context.guild

    @property
    def channel(self):
        return self.context.channel

    async def on_timeout(self):
        if self._disabled or self.message is None:
            return

        self._disable_children()
        await self.message.edit(view=self)

    def _disable_children(self):
        for item in self.children:
            if _can_be_disabled(item):
                item.disabled = True  # type: ignore

    async def interaction_check(self, interaction):
        return interaction.user.id == self.context.author.id

    async def start(self):
        await self.update()
        return await self.wait()

    async def update(self):
        await self.update_components()
        content = await self.get_content()

        kwargs = {'content': content, 'view': self}

        if self.message is not None:
            await self.message.edit(**kwargs)
        else:
            self.message = await self.context.send(**kwargs)

    async def get_content(self):
        raise NotImplementedError

    async def update_components(self):
        pass  # This is optional to implement

    @contextlib.asynccontextmanager
    async def disable(self, interaction=None):
        if self.message is None:
            raise RuntimeError('Missing message to edit.')

        items = [x for x in self.children if _can_be_disabled(x)]
        state = [x.disabled for x in items]  # type: ignore :blobpain:

        try:
            self._disabled = True

            for item in items:
                item.disabled = True  # type: ignore

            if interaction is None or interaction.response.is_done():
                await self.message.edit(view=self)
            else:
                await interaction.response.edit_message(view=self)

            yield
        finally:
            self._disabled = False

            for item, previous in zip(items, state):
                item.disabled = previous  # type: ignore

            if not self.is_finished():
                await self.update()

    async def pick(self, message, *, placeholder=None, options, interaction):
        view = _PickMenu(context=self.context, placeholder=placeholder, options=options)
        return await self._prompt_and_wait_for_result(message, view=view, interaction=interaction)

    async def choose(self, message, *, choices, interaction):
        view = _ChooseMenu(context=self.context, choices=choices)
        return await self._prompt_and_wait_for_result(message, view=view, interaction=interaction)

    async def _prompt_and_wait_for_result(self, message, *, view, interaction):
        prompt = await interaction.followup.send(message, view=view, wait=True)

        await view.wait()
        await prompt.delete()

        if view.result is not None:
            return view.result
        else:
            raise asyncio.TimeoutError

    async def prompt(self, question, *, check=None, interaction):
        view = CancellableMenu(context=self.context)
        prompt = await interaction.followup.send(question, view=view, wait=True)

        def message_check(message):
            if message.author != self.context.author:
                return

            if message.channel != self.context.channel:
                return

            return check(message.content) if check is not None else True

        try:
            cancel_task = create_task(view.wait())
            wait_for_task = create_task(self.mousey.wait_for('message', check=message_check))

            done, pending = await asyncio.wait(
                {cancel_task, wait_for_task}, timeout=MENU_TIMEOUT, return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if not done or cancel_task in done:  # asyncio.wait does not raise TimeoutError
                raise asyncio.TimeoutError
        finally:
            await prompt.delete()

        response = await next(iter(done))

        if self.channel.permissions_for(self.context.me).manage_messages:
            await response.delete()

        return response.content


class _StopButton(discord.ui.Button):
    async def callback(self, interaction):
        view = self.view

        if view is None:
            raise RuntimeError('Missing view to disable.')

        view.stop()
        view._disable_children()

        if view.message is not None:
            await interaction.response.edit_message(view=view)


class ExitableMenu(Menu):
    def __init__(self, *, context):
        super().__init__(context=context)

        self.add_item(_StopButton(label='Exit'))


class CancellableMenu(Menu):
    def __init__(self, *, context):
        super().__init__(context=context)

        self.add_item(_StopButton(label='Cancel'))


class _PickMenu(CancellableMenu):
    def __init__(self, *, context, placeholder=None, options):
        super().__init__(context=context)

        self.result = None

        if placeholder is not None:
            self.pick.placeholder = placeholder

        for option in options:
            if isinstance(option, discord.SelectOption):
                self.pick.append_option(option)
            else:
                self.pick.add_option(label=option)

    @discord.ui.select()
    async def pick(self, select, interaction):
        self.stop()
        self.result = select.values[0]


class _ChooseButton(discord.ui.Button):
    async def callback(self, interaction):
        view = self.view

        if view is None:
            raise RuntimeError('Missing view to alter.')

        view.stop()
        view.result = self.label


class _ChooseMenu(Menu):
    def __init__(self, *, context, choices):
        super().__init__(context=context)

        self.result = None

        for choice in choices:
            self.add_item(_ChooseButton(style=discord.ButtonStyle.primary, label=choice))

        # We can't inherit from CancellabelMenu
        # As add_item puts items behind the others
        self.add_item(_StopButton(label='Cancel'))
