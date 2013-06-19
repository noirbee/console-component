# -*- coding: utf-8 -*-

import sys
import traceback
import Levenshtein
from output.output import Output
from output.console_output import ConsoleOutput
from input.argv_input import ArgvInput
from input.list_input import ListInput
from input.input_argument import InputArgument
from input.input_option import InputOption
from input.input_definition import InputDefinition
from command.command import Command
from command.help_command import HelpCommand
from command.list_command import ListCommand
from helper.helper_set import HelperSet
from helper.formatter_helper import FormatterHelper
from helper.dialog_helper import DialogHelper


class Application(object):
    """
    An Application is the container for a collection of commands.

    This class is optimized for a standard CLI environment.

    Usage:
    >>> app = Application('myapp', '1.0 (stable)')
    >>> app.add(HelpCommand())
    >>> app.run()
    """

    def __init__(self, name='UNKNOWN', version='UNKNOWN'):
        """
        Constructor

        @param name: The name of the application
        @type name: basestring
        @param version: The version of the application
        @type version: basestring
        """
        self.__name = name
        self.__version = version
        self.__catch_exceptions = True
        self.__auto_exit = True
        self.__commands = {}
        self.__definition = self.get_default_input_definition()
        self.__want_helps = False
        self.__helper_set = self.get_default_helper_set()

        for command in self.get_default_commands():
            self.add(command)

    def run(self, input_=None, output_=None):
        """
        Runs the current application

        @param input_: An Input Instance
        @type input_: Input
        @param output_: An Output instance
        @type output_: Output

        @return: 0 if everything went fine, or an error code
        @rtype: int
        """
        if input_ is None:
            input_ = ArgvInput()

        if output_ is None:
            output_ = ConsoleOutput()

        try:
            status_code = self.do_run(input_, output_)
        except Exception, e:
            if not self.__catch_exceptions:
                exc = sys.exc_info()
                raise exc[1], None, exc[2]

            if isinstance(output_, ConsoleOutput):
                self.render_exception(e, output_.get_error_output())
            else:
                self.render_exception(e, output_)

            status_code = e.errno if hasattr(e, 'errno') else 1

        if self.__auto_exit:
            if status_code > 255:
                status_code = 255

            exit(status_code)

        return status_code

    def do_run(self, input_, output_):
        """
        Runs the current application

        @param input_: An Input Instance
        @type input_: Input
        @param output_: An Output instance
        @type output_: Output

        @return: 0 if everything went fine, or an error code
        @rtype: int
        """
        name = self.get_command_name(input_)

        if input_.has_parameter_option(['--ansi']):
            output_.set_decorated(True)
        elif input_.has_parameter_option(['--no-ansi']):
            output_.set_decorated(False)

        if input_.has_parameter_option(['--help', '-h']):
            if not name:
                name = 'help'
                input_ = ListInput([('command', 'help')])
            else:
                self.__want_helps = True

        if input_.has_parameter_option(['--no-interaction', '-n']):
            input_.set_interactive(False)

        if input_.has_parameter_option(['--quiet', '-q']):
            output_.set_verbosity(Output.VERBOSITY_QUIET)
        elif input_.has_parameter_option(['--verbose', '-v']):
            output_.set_verbosity(Output.VERBOSITY_VERBOSE)

        if not name:
            name = 'list'
            input_ = ListInput([('command', 'list')])

        # the command name MUST be the first element of the input
        command = self.find(name)
        self.__running_commmand = command
        status_code = command.run(input_, output_)
        self.__running_commmand = None

        return status_code

    def set_helper_set(self, helper_set):
        self.__helper_set = helper_set

    def get_helper_set(self):
        return self.__helper_set

    def set_definition(self, definition):
        self.__definition = definition

    def get_definition(self):
        return self.__definition

    def get_help(self):
        messages = [
            self.get_long_version(),
            '',
            '<comment>Usage:</comment>',
            '  command [arguments] [options]',
            '',
            '<comment>Options:</comment>'
        ]

        for option in self.get_definition().get_options():
            messages.append('  %-29s %s %s'
                            % ('<info>--' + option.get_name() + '</info>',
                               '<info>-' + option.get_shortcut() + '</info>' if option.get_shortcut() else '  ',
                               option.get_description()))

        return '\n'.join(messages)

    def set_catch_exceptions(self, boolean):
        self.__catch_exceptions = boolean

    def set_auto_exit(self, boolean):
        self.__auto_exit = boolean

    def get_name(self):
        return self.__name

    def set_name(self, name):
        self.__name = name

    def get_version(self):
        return self.__version

    def set_version(self, version):
        self.__version = version

    def get_long_version(self):
        if 'UNKNOWN' != self.get_name() and 'UNKNOWN' != self.get_version():
            return '<info>%s</info> version <comment>%s</comment>' % (self.get_name(), self.get_version())

        return '<info>Console Tool</info>'

    def register(self, name):
        return self.add(Command(name))

    def add_commands(self, commands):
        for command in commands:
            self.add(command)

    def add(self, command):
        command.set_application(self)

        if not command.is_enabled():
            command.set_application(None)

            return

        self.__commands[command.get_name()] = command

        for alias in command.get_aliases():
            self.__commands[alias] = command

        return command

    def get(self, name):
        if name not in self.__commands:
            raise Exception('The command "%s" does not exist.' % name)

        command = self.__commands[name]

        if self.__want_helps:
            self.__want_helps = False

            help_command = self.get('help')
            help_command.set_command(command)

            return help_command

        return command

    def has(self, name):
        return name in self.__commands

    def get_namespaces(self):
        namespaces = []
        for command in self.__commands.values():
            namespaces.append(self.extract_namespace(command.get_name()))

            for alias in command.get_aliases():
                namespaces.append(self.extract_namespace(alias))

        return list(set(namespaces))

    def find_namespace(self, namespace):
        all_namespaces = {}
        for n in self.get_namespaces():
            all_namespaces[n] = n.split(':')

        found = []
        for i, part in enumerate(namespace.split(':')):
            abbrevs = self.get_abbreviations(
                list(
                    set(
                        filter(
                            None,
                            map(
                                lambda p: p[i] if len(p) > i else '',
                                all_namespaces.values()
                            )
                        )
                    )
                )
            )

            if not part in abbrevs:
                message = 'There are no commands defined in the "%s" namespace.' % namespace

                if 1 <= i:
                    part = ':'.join(found) + ':' + part

                alternatives = self.find_alternative_namespace(part, abbrevs)
                if alternatives:
                    if len(alternatives) == 1:
                        message += '\n\nDid you mean this?\n    '
                    else:
                        message += '\n\nDid you mean one of these?\n    '

                    message += '\n    '.join(alternatives)

                raise Exception(message)

            if len(abbrevs[part]) > 1:
                raise Exception('The namespace "%s" is ambiguous (%s).'
                                % (namespace, self.get_abbreviation_suggestions(abbrevs[part])))

            found.append(abbrevs[part][0])

        return ':'.join(found)

    def find(self, name):
        # namespace
        namespace = ''
        search_name = name
        pos = name.find(':')
        if pos != -1:
            namespace = self.find_namespace(name[:pos])
            search_name = namespace + name[pos:]

        # name
        commands = []
        for command in self.__commands.values():
            extracted_namespace = self.extract_namespace(command.get_name())
            if extracted_namespace == namespace or namespace and extracted_namespace.find(namespace) == 0:
                commands.append(command.get_name())

        abbrevs = self.get_abbreviations(list(set(commands)))
        if search_name in abbrevs and len(abbrevs[search_name]) == 1:
            return self.get(abbrevs[search_name][0])

        if search_name in abbrevs and len(abbrevs[search_name]) > 1:
            suggestions = self.get_abbreviation_suggestions(abbrevs[search_name])

            raise Exception('Command "%s" is ambiguous (%s).' % (name, suggestions))

        # aliases
        aliases = []
        for command in self.__commands.values():
            for alias in command.get_aliases():
                extracted_namespace = self.extract_namespace(alias)
                if extracted_namespace == alias or namespace and extracted_namespace.find(namespace) == 0:
                    aliases.append(alias)

        aliases = self.get_abbreviations(list(set(aliases)))
        if search_name not in aliases:
            message = 'Command "%s" is not defined.' % name

            alternatives = self.find_alternative_commands(search_name, abbrevs)
            if alternatives:
                if len(alternatives) == 1:
                    message += '\n\nDid you mean this?\n    '
                else:
                    message += '\n\nDid you mean one of these?\n    '

                message += '\n    '.join(alternatives)

            raise Exception(message)

        if len(aliases[search_name]) > 1:
            raise Exception('Command "%s" is ambiguous (%s).'
                            % (name, self.get_abbreviation_suggestions(aliases[search_name])))

        return self.get(aliases[search_name][0])

    def all(self, namespace=None):
        if namespace is None:
            return self.__commands

        commands = {}
        for name, command in self.__commands.items():
            if namespace == self.extract_namespace(name, namespace.count(':') + 1):
                commands[name] = command

        return commands

    @classmethod
    def get_abbreviations(cls, names):
        abbrevs = {}
        for name in names:
            l = len(name)
            while l > 0:
                abbrev = name[:l]
                if not abbrev in abbrevs:
                    abbrevs[abbrev] = [name]
                else:
                    abbrevs[abbrev].append(name)

                l -= 1

        for name in names:
            abbrevs[name] = [name]

        return abbrevs

    def as_text(self, namespace=None, raw=False):
        commands = self.all(self.find_namespace(namespace)) if namespace else self.__commands

        width = 0
        for command in commands.values():
            width = len(command.get_name()) if len(command.get_name()) > width else width
        width += 2

        if raw:
            messages = []
            for space, commands in self.sort_commands(commands):
                for name, command in commands:
                    messages.append('%-*s %s' % (width, name, command.get_description()))

                return '\n'.join(messages)

        messages = [self.get_help(), '']
        if namespace:
            messages.append('<comment>Available commands for the \"%s\" namespace:</comment>' % namespace)
        else:
            messages.append('<comment>Available commands:</comment>')

        # add command by namespace
        for space, commands in self.sort_commands(commands):
            if not namespace and '_global' != space:
                messages.append('  <comment>' + space + '</comment>')

            for name, command in commands:
                messages.append('  <info>' + '%-*s</info> %s' % (width, name, command.get_description()))

        return '\n'.join(messages)

    def render_exception(self, e, output_):
        if output_.get_verbosity() == Output.VERBOSITY_VERBOSE:
            error = traceback.format_exc()
        else:
            error = str(e)

        error = str(error).split('\n\n', 1)
        output_.writeln('<error>%s</error><comment>%s</comment>'
                        % (error[0], '\n\n' + error[1] if len(error) > 1 else ''))

    def get_command_name(self, input_):
        return input_.get_first_argument()

    def get_default_input_definition(self):
        return InputDefinition([
            InputArgument('command', InputArgument.REQUIRED, 'The command to execute.'),

            InputOption('--help', '-h', InputOption.VALUE_NONE, 'Display this help message.'),
            InputOption('--quiet', '-q', InputOption.VALUE_NONE, 'Do not output any message.'),
            InputOption('--verbose', '-v', InputOption.VALUE_NONE, 'Increase verbosity of messages.'),
            InputOption('--version', '-V', InputOption.VALUE_NONE, 'Display this application version.'),
            InputOption('--ansi', '', InputOption.VALUE_NONE, 'Force ANSI output.'),
            InputOption('--no-ansi', '', InputOption.VALUE_NONE, 'Disable ANSI output.'),
            InputOption('--no-interaction', '-n', InputOption.VALUE_NONE, 'Do not ask any interactive question.')
        ])

    def get_default_commands(self):
        return [HelpCommand(), ListCommand()]

    def get_default_helper_set(self):
        return HelperSet({
            'formatter': FormatterHelper(),
            'dialog': DialogHelper()
        })

    def sort_commands(self, commands):
        """
        Sorts command in alphabetical order

        @param commands: A dict of commands
        @type commands: dict

        @return: A sorted list of commands
        """
        namespaced_commands = {}
        for name, command in commands.items():
            key = self.extract_namespace(name, 1)
            if not key:
                key = '_global'

            if key in namespaced_commands:
                namespaced_commands[key][name] = command
            else:
                namespaced_commands[key] = {name: command}

        for name, command in namespaced_commands.get('_global', {}).items():
            if name in namespaced_commands:
                namespaced_commands[name][name] = namespaced_commands['_global'].pop(name)

        for namespace, commands in namespaced_commands.items():
            namespaced_commands[namespace] = sorted(commands.items(), key=lambda x: x[0])

        namespaced_commands = sorted(namespaced_commands.items(), key=lambda x: x[0])

        return namespaced_commands

    def get_abbreviation_suggestions(self, abbrevs):
        return '%s, %s%s' % (abbrevs[0], abbrevs[1], ' and %d more' % (len(abbrevs) - 2) if len(abbrevs) > 2 else '')

    def extract_namespace(self, name, limit=None):
        parts = name.split(':')
        parts.pop()

        return ':'.join(parts[:limit] if limit else parts)

    def find_alternative_commands(self, name, abbrevs):
        def callback(item):
            return item.get_name()

        return self.find_alternatives(name, self.__commands.values(), abbrevs, callback)

    def find_alternative_namespace(self, name, abbrevs):
        return self.find_alternatives(name, self.get_namespaces(), abbrevs)

    def find_alternatives(self, name, collection, abbrevs, callback=None):
        alternatives = {}

        for item in collection:
            if callback is not None:
                item = callback(item)

            lev = Levenshtein.distance(name, item)
            if lev <= len(name) / 3 or item.find(name) != -1:
                alternatives[item] = lev

        if not alternatives:
            for key, values in abbrevs.items():
                lev = Levenshtein.distance(name, key)
                if lev <= len(name) / 3 or key.find(name) != -1:
                    for value in values:
                        alternatives[value] = lev

        asorted = sorted(alternatives.items(), key=lambda x: x[1])

        return map(lambda x: x[0], asorted)