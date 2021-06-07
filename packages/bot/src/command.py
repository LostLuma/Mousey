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

from discord.ext import commands


# Require at least one argument for Greedy[...]
# Adjust signature to signal the Greedy changes
class Command(commands.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.greedy_require_arg = kwargs.get('greedy_require_arg', True)

    async def _transform_greedy_pos(self, ctx, param, required, converter):
        if not self.greedy_require_arg:
            return await super()._transform_greedy_pos(ctx, param, required, converter)

        result = []
        error = None

        view = ctx.view

        while not view.eof:
            # For use with a manual undo
            previous = view.index

            view.skip_ws()
            argument = view.get_quoted_word()

            try:
                value = await commands.run_converters(ctx, converter, argument, param)
            except (commands.ArgumentParsingError, commands.CommandError) as e:
                error = e
                view.index = previous

                break
            else:
                result.append(value)

        if not result:
            if not required:
                return param.default
            elif error is not None:
                raise error
            else:
                raise commands.MissingRequiredArgument(param)

        return result

    @property
    def signature(self):
        if self.usage is not None:
            return self.usage

        params = self.clean_params

        if not params:
            return ''

        result = []

        # Replaces all instances of greedy and greedy_require_arg with <param...>
        # Moves the indicator for greedy/positional into the parameter definition
        for name, param in params.items():
            greedy = '...' if isinstance(param.annotation, commands.Greedy) else ''

            if param.default is not param.empty:
                if isinstance(param.default, str):
                    has_default = param.default
                else:
                    has_default = param.default is not None

                if not has_default:
                    result.append(f'[{name}{greedy}]')
                else:
                    result.append(f'[{name}={param.default}{greedy}]')
            elif param.kind == param.VAR_POSITIONAL:
                if self.require_var_positional:
                    result.append(f'<{name}...>')
                else:
                    result.append(f'[{name}...]')
            elif greedy:
                if self.greedy_require_arg:
                    result.append(f'<{name}...>')
                else:
                    result.append(f'[{name}...]')
            elif self._is_typing_optional(param.annotation):
                result.append(f'[{name}]')
            else:
                result.append(f'<{name}>')

        return ' '.join(result)


# Redeclare shortcut decorators to use subclassed Command
class Group(commands.Group, Command):
    def command(self, *args, **kwargs):
        kwargs.setdefault('parent', self)

        def decorator(func):
            result = command(*args, **kwargs)(func)
            self.add_command(result)

            return result

        return decorator

    def group(self, *args, **kwargs):
        kwargs.setdefault('parent', self)

        def decorator(func):
            result = group(*args, **kwargs)(func)
            self.add_command(result)

            return result

        return decorator


def command(name=None, cls=Command, **kwargs):
    return commands.command(name, cls=cls, **kwargs)


def group(name=None, cls=Group, **kwargs):
    defaults = {
        'case_insensitive': True,
        'invoke_without_command': True,
    }

    return command(name, cls=cls, **defaults | kwargs)
