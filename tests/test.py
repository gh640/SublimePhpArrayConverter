# coding: utf-8

"""Tests PhpArrayConverter functions.
"""

import sys
import sublime
import textwrap
from unittest import TestCase


class TestPhpArrayConverterConvertCommand(TestCase):
    """Tests the converter command.
    """

    def setUp(self):
        self.view = sublime.active_window().new_file()
        syntax = self.view.settings().set("syntax", "PHP.sublime-syntax")

    def tearDown(self):
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")

    def test_simple_array(self):
        text = '<?php $a = array();'
        expected = '<?php $a = [];'

        self.setText(text)
        self.view.run_command('php_array_converter_convert')
        self.assertEqual(self.getText(), expected)

    def setText(self, string):
        self.view.run_command("insert", {"characters": string})

    def getText(self):
        content = self.view.substr(sublime.Region(0, self.view.size()))
        return content


PhpArrayConverter = sys.modules["PhpArrayConverter.PhpArrayConverter"]


class TestPhpTokenizer(TestCase):
    """Tests the PhpTokenizer.
    """

    def setUp(self):
        settings = {}
        self.tokenizer = PhpArrayConverter.PhpTokenizer(settings)

    def test_simple_array_tokenization(self):
        text = '<?php $a = array(); '
        expected_beginning = '{"tokens":[["T_OPEN_TAG","<?php ",1]'

        self.tokenizer.run(text)
        result = self.tokenizer.stdout

        self.assertTrue(result.startswith(expected_beginning))


class TestConvertedCoderGenerator(TestCase):
    """Tests the ConvertedCoderGenerator.
    """

    def setUp(self):
        self.code_generator = PhpArrayConverter.ConvertedCoderGenerator()

    def test_run(self):
        tokenizer_stdout = """{"tokens":[["T_OPEN_TAG","<?php\\n",1],["T_WHITESPACE","\\n",2],[312,"$a",3],["T_WHITESPACE"," ",3],"=",["T_WHITESPACE"," ",3],["T_ARRAY","array",3],"(",["T_WHITESPACE","\\n  ",3],[318,"'foo'",4],["T_WHITESPACE"," ",4],[364,"=>",4],["T_WHITESPACE"," ",4],["T_ARRAY","array",4],"(",[295,"(string)",4],["T_WHITESPACE"," ",4],[308,"5",4],",",["T_WHITESPACE"," ",4],[297,"(int)",4],["T_WHITESPACE"," ",4],[309,"10.5",4],")",",",["T_WHITESPACE","\\n  ",4],[318,"'bar'",5],["T_WHITESPACE"," ",5],[364,"=>",5],["T_WHITESPACE"," ",5],[308,"300",5],",",["T_WHITESPACE","\\n",5],")",";",["T_WHITESPACE","\\n",6]]}"""
        expected = """<?php\n\n$a = [\n  'foo' => [(string) 5, (int) 10.5],\n  'bar' => 300,\n];\n"""

        self.code_generator.run(tokenizer_stdout)
        actual = self.code_generator.code_converted

        self.assertEqual(actual, expected)
