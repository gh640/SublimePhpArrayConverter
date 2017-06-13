# coding: utf-8

"""Convert array syntax in php files.
"""

import os
import json
from subprocess import Popen, PIPE
# import threading

import sublime
import sublime_plugin

__version__ = '0.1.1'
__author__ = 'Goto Hayato'
__copyright__ = 'Copyright 2017, Goto Hayato'
__license__ = 'MIT'


class PhpArrayConverterConvertEvents(sublime_plugin.EventListener):
    """EventListener class.
    """

    def on_pre_save(self, view):
        """Runs array conversion when a file is being saved.
        """
        settings = sublime.load_settings("PhpArrayConverter.sublime-settings")
        auto_convert_on_save = settings.get("auto_convert_on_save", False)

        if auto_convert_on_save:
            view.run_command('php_array_converter_convert')


class PhpArrayConverterConvertCommand(sublime_plugin.TextCommand):
    """Sublime text command for php array conversion.
    """

    def run(self, edit):
        self.settings = sublime.load_settings(
            "PhpArrayConverter.sublime-settings")
        self.is_open_tag_prepended = False

        if self.check_syntax() and self.check_selection():
            self.convert_array(edit)

    def check_syntax(self):
        syntax = self.view.settings().get("syntax")
        if syntax.find('PHP.sublime-syntax') == -1:
            sublime.status_message(
                "PhpArrayConverter works only for PHP files.")
            return False

        return True

    def check_selection(self):
        if len(self.view.sel()) > 1:
            sublime.status_message(
                "PhpArrayConverter doesn't support multiple selection.")
            return False

        return True

    def convert_array(self, edit):
        code = self.get_text()
        code = self.add_open_tag(code)

        tokenizer = PhpTokenizer(self.settings)
        tokenizer.run(code)

        if tokenizer.returncode == 1:
            sublime.status_message(
                "PhpArrayConverter tokenizer failed: {}.".format(self.stderr))
            return

        code_generator = ConvertedCoderGenerator()
        code_generator.run(tokenizer.stdout)

        code_converted = code_generator.code_converted
        code_converted = self.remove_open_tag(code_converted)

        selection = self.view.sel()[0] if self.view.sel()[0] else None
        replacer = TextReplacer()
        replacer.run(self.view, edit, code_converted, selection)

        sublime.status_message('PhpArrayConverter completed successfully.')

    def add_open_tag(self, text, open_tag='<?php'):
        if not text.startswith(open_tag):
            text = open_tag + text
            self.is_open_tag_prepended = True

        return text

    def remove_open_tag(self, text, open_tag='<?php'):
        if self.is_open_tag_prepended:
            text = text[len(open_tag):]

        return text

    def get_text(self):
        content = self.view.substr(self.view.sel()[0])
        if not content:
            content = self.view.substr(sublime.Region(0, self.view.size()))

        return content


class PhpTokenizer(object):
    """Runs php tokenizer.
    """

    def __init__(self, settings):
        self.settings = settings

    def run(self, text):
        try:
            process = Popen(
                self.get_php_cmd(),
                env=self.get_env(),
                shell=sublime.platform() == 'windows',
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE
            )
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
        """Generates code whose array syntax is converted.
        """
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
