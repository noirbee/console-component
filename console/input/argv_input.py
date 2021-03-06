# -*- coding: utf-8 -*-

import sys
from input import Input


class ArgvInput(Input):

    def __init__(self, definition=None):
        super(ArgvInput, self).__init__(definition)

        self.__tokens = sys.argv
        self.__tokens.pop(0)
        self.__parsed = None

    def parse(self):
        parse_options = True
        self.__parsed = self.__tokens
        while True:
            try:
                token = self.__parsed.pop(0)
            except IndexError:
                break

            if parse_options and token == '':
                self.parse_argument(token)
            elif parse_options and token == '--':
                parse_options = False
            elif parse_options and token.find('--') == 0:
                self.parse_long_option(token)
            elif parse_options and token[0] == '-':
                self.parse_short_option(token)
            else:
                self.parse_argument(token)

    def parse_short_option(self, token):
        name = token[1:]

        if len(name) > 1:
            if self.definition.has_shortcut(name[0]) and self.definition.get_option_for_shortcut(name[0]).accept_value():
                # an option with a value (with no space)
                self.add_short_option(name[0], name[1:])
            else:
                self.parse_short_option_set(name)
        else:
            if self.definition.has_shortcut(name) and self.definition.get_option_for_shortcut(name).accept_value():
                try:
                    value = self.__parsed.pop(0)
                except IndexError:
                    value = None

                if value.startswith('-'):
                    self.__parsed.insert(0, value)
                    value = None

                self.add_short_option(name, value)
            else:
                self.add_short_option(name, None)

    def parse_short_option_set(self, name):
        l = len(name)
        for i in range(0, l):
            if not self.definition.has_shortcut(name[i]):
                raise Exception('The "-%s" option does not exist.' % name[i])

            option = self.definition.get_option_for_shortcut(name[i])
            if option.accept_value():
                self.add_long_option(option.get_name(), None if l - 1 == i else name[i + 1:])

                break
            else:
                self.add_long_option(option.get_name(), True)

    def parse_long_option(self, token):
        name = token[2:]
        pos = name.find('=')
        if pos != -1:
            self.add_long_option(name[:pos], name[pos + 1:])
        else:
            if self.definition.has_option(name) and self.definition.get_option(name).accept_value():
                try:
                    value = self.__parsed.pop(0)
                except IndexError:
                    value = None

                if value.startswith('-'):
                    self.__parsed.insert(0, value)
                    value = None

                self.add_long_option(name, value)
            else:
                self.add_long_option(name, None)

    def parse_argument(self, token):
        c = len(self.arguments)

        # if input is expecting another argument, add it
        if self.definition.has_argument(c):
            arg = self.definition.get_argument(c)
            self.arguments[arg.get_name()] = [token] if arg.is_array() else token
        elif self.definition.has_argument(c - 1) and self.definition.get_argument(c - 1).is_array():
            arg = self.definition.get_argument(c - 1)
            self.arguments[arg.get_name()].append(token)
        # unexpected argument
        else:
            raise Exception('Too many arguments')

    def add_short_option(self, shortcut, value):
        if not self.definition.has_shortcut(shortcut):
            raise Exception('The "-%s" option does not exist.' % shortcut)

        self.add_long_option(self.definition.get_option_for_shortcut(shortcut).get_name(), value)

    def add_long_option(self, name, value):
        if not self.definition.has_option(name):
            raise Exception('The "--%s" option does not exist.' % name)

        option = self.definition.get_option(name)

        if value is None and option.accept_value() and len(self.__parsed):
            # if option accepts an optional or mandatory argument
            # let's see if there is one provided
            try:
                nxt = self.__parsed.pop(0)
            except IndexError:
                nxt = None

            if len(nxt) >= 1 and nxt[0] == '-':
                value = nxt
            elif not nxt:
                value = ''
            else:
                self.__parsed.insert(0, nxt)

        if value is None:
            if option.is_value_required():
                raise Exception('The "--%s" option requires a value.' % name)

            value = option.get_default() if option.is_value_optional() else True

        if option.is_array():
            if name not in self.options:
                self.options[name] = [value]
            else:
                self.options[name].append(value)
        else:
            self.options[name] = value

    def get_first_argument(self):
        for token in self.__tokens:
            if token and token[0] == '-':
                continue

            return token

    def has_parameter_option(self, values):
        values = [values] if not isinstance(values, (list, tuple)) else values

        for v in self.__tokens:
            if v in values:
                return True

        return False

    def get_parameter_option(self, values, default=False):
        values = [values] if not isinstance(values, (list, tuple)) else values

        tokens = self.__tokens
        while True:
            try:
                token = tokens.pop(0)
            except IndexError:
                break

            for value in values:
                if token.find(value) == 0:
                    pos = token.find('=')
                    if pos != -1:
                        return token[:pos+1]

                    return tokens.pop(0)

        return default