# coding: utf-8

"""Convert array syntax in php files.
"""

import os
import json
import subprocess
# import threading

import sublime
import sublime_plugin

__version__ = '0.1.4'
__author__ = 'Goto Hayato'
__copyright__ = 'Copyright 2017, Goto Hayato'
__license__ = 'MIT'

SETTINGS_KEY = 'PhpArrayConverter.sublime-settings'


class PhpArrayConverterConvertEvents(sublime_plugin.EventListener):
    """Sublime text EventListener class.
    """

    def on_pre_save(self, view):
        """Runs array conversion when a file is being saved.
        """
        settings = sublime.load_settings(SETTINGS_KEY)
        auto_convert_on_save = settings.get("auto_convert_on_save", False)

        if auto_convert_on_save:
            params = {'force_whole': True}
            view.run_command('php_array_converter_convert', params)


class PhpArrayConverterConvertCommand(sublime_plugin.TextCommand):
    """Sublime text TextCommand for php array conversion.
    """

    OPEN_TAG = '<?php'

    def run(self, edit, force_whole=False):
        """Runs the command.
        """
        self.force_whole = force_whole
        self.is_open_tag_prepended = False

        if self.check_syntax() and self.check_selection():
            self.convert_array(edit)

    def check_syntax(self):
        if not self.is_php():
            self.show_message('{0[pkg]} works only for PHP files.')
            return False
        return True

    def is_php(self):
        return 'PHP' in self.view.settings().get('syntax')

    def check_selection(self):
        if len(self.view.sel()) > 1:
            self.show_message("{0[pkg]} doesn't support multiple selection.")
            return False
        return True

    def convert_array(self, edit):
        if self.force_whole:
            region_orig = sublime.Region(0, self.view.size())
        else:
            region_orig = self.get_region()

        code_orig = self.get_text(region_orig)
        code_orig = self.add_open_tag(code_orig)

        settings = sublime.load_settings(SETTINGS_KEY)
        tokenizer = PhpTokenizer({'path': settings.get('path', False)})
        tokenizer.run(code_orig)

        if tokenizer.returncode != 0:
            params = {'error': tokenizer.stderr}
            self.show_message('{0[pkg]} tokenizer failed: {0[error]}', params)
            return

        generator = ConvertedCoderGenerator()
        generator.run(tokenizer.stdout)

        code_converted = generator.code_converted
        code_converted = self.remove_open_tag(code_converted)

        self.view.replace(edit, region_orig, code_converted)

        self.show_message('{0[pkg]} completed successfully.')

    def add_open_tag(self, text):
        if not text.startswith(self.OPEN_TAG):
            text = self.OPEN_TAG + text
            self.is_open_tag_prepended = True
        return text

    def remove_open_tag(self, text):
        if self.is_open_tag_prepended:
            text = text[len(self.OPEN_TAG):]
        return text

    def get_region(self):
        region = self.view.sel()[0]
        if region.empty():
            region = sublime.Region(0, self.view.size())
        return region

    def get_text(self, region):
        return self.view.substr(region)

    def show_message(self, message, params=None):
        if not params:
            params = {}
        params['pkg'] = 'PhpArrayConverter'
        sublime.status_message(message.format(params))


class PhpTokenizer(object):
    """Runs php tokenizer.
    """

    def __init__(self, settings):
        self.settings = settings

    def run(self, text):
        popen_args = {
            'args': self.get_php_cmd(),
            'env': self.get_env(),
            'stdin': subprocess.PIPE,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
        }

        # Prevent cmd.exe window popup on Windows.
        if sublime.platform() == 'windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            popen_args['startupinfo'] = startupinfo

        try:
            process = subprocess.Popen(**popen_args)
            stdout, stderr = process.communicate(input=self.encode(text))

            self.stdout = self.decode(stdout)
            self.stderr = self.decode(stderr)
            self.returncode = process.returncode
        except OSError as e:
            self.stderr = str(e)
            self.returncode = 1

    def get_php_cmd(self):
        tokenizer = os.path.join(os.path.dirname(__file__), 'tokenizer.php')
        return ['php', tokenizer]

    def get_env(self):
        env = os.environ.copy()

        if self.settings.get('path', False):
            env['PATH'] = self.settings.get('path')

        return env

    def encode(self, text):
        return text.encode('utf-8')

    def decode(self, text):
        return text.decode('utf-8')


class ConvertedCoderGenerator(object):
    """Generates array-converted php code.
    """

    def run(self, stdout):
        tokens = self.parse_json(stdout)
        tokens_normalized = self.normalize_tokens(tokens)
        code_converted = self.gen_converted_code(tokens_normalized)

        self.code_converted = code_converted

    def parse_json(self, json_string):
        try:
            json_parsed = json.loads(json_string)
        except Exception as e:
            raise Exception("JSON is not valid.")

        tokens = json_parsed.get('tokens')

        if not tokens:
            raise Exception("Passed JSON doesn't have proper properties.")

        return tokens

    def normalize_tokens(self, tokens):
        return [[t, t, None] if type(t) is str else t for t in tokens]

    def gen_converted_code(self, tokens):
        replacements = {}
        for i, t1 in enumerate(tokens):
            if PhpToken.equals('T_ARRAY', t1[0]):
                is_array_opened = False
                is_array_closed = False
                i_next = i + 1
                i_open = None
                i_close = None

                # Find the matching open brace.
                for j, t2 in enumerate(tokens[i_next:]):
                    if PhpToken.equals('T_WHITESPACE', t2[0]):
                        continue

                    if PhpToken.equals('BRACE_OPEN', t2[0]):
                        i_open = i_next + j
                        is_array_opened = True

                    # Break if any element other than space comes.
                    break

                # Find the matching close brace.
                if is_array_opened:
                    depth = 0
                    for j, t2 in enumerate(tokens[i_next:]):
                        if PhpToken.equals('BRACE_OPEN', t2[0]):
                            depth += 1
                        elif PhpToken.equals('BRACE_CLOSE', t2[0]):
                            depth -= 1
                            if depth == 0:
                                i_close = i_next + j
                                is_array_closed = True
                                break

                # Register replacements if a set of array, open brace and close
                # brace are found.
                if is_array_opened and is_array_closed:
                    replacements[i] = ['[', '[', None]
                    for k in range(i_next, i_open + 1):
                        replacements[k] = ['', '', None]
                    replacements[i_close] = [']', ']', None]

        tokens_converted = []
        for i, t in enumerate(tokens):
            try:
                token = replacements[i]
            except KeyError as e:
                token = t
            tokens_converted.append(token)

        return ''.join(x[1] for x in tokens_converted)


class TextReplacer(object):
    """Replaces text with specified string.
    """

    def run(self, view, edit, text, selection=None):
        if not selection:
            selection = sublime.Region(0, view.size())
        view.replace(edit, selection, text)


class PhpToken(object):
    """Checks php tokens.
    """

    TOKEN_MAP = {
        'T_OPEN_TAG': 'T_OPEN_TAG',
        'T_ARRAY': 'T_ARRAY',
        'T_WHITESPACE': 'T_WHITESPACE',
        'BRACE_OPEN': '(',
        'BRACE_CLOSE': ')',
    }

    @classmethod
    def equals(cls, code, value):
        return cls.TOKEN_MAP[code] == value
