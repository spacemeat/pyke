''' Unit test for options module. '''

#pylint: disable=missing-class-docstring, missing-function-docstring

import difflib
import unittest
from pyke.utilities import WorkingSet
from pyke.options_parser import (Ast, TokenObj as TO, Token as T)

WorkingSet.colors = {
    'off':              {'form': 'named', 'off': [] },
    'token_type':       {'form': 'rgb24', 'fg': [0x33, 0xff, 0xff] },
    'token_value':      {'form': 'rgb24', 'fg': [0xff, 0x33, 0xff] },
    'token_depth':      {'form': 'rgb24', 'fg': [0x33, 0xff, 0x33] },
}

class TestCase_NoDiff(unittest.TestCase):
    def assertEqual(self, first, second, msg=None):
        if first != second:
            #diff = difflib.unified_diff(
            diff = difflib.ndiff(
                #first.splitlines(keepends=True),
                #second.splitlines(keepends=True),
                #str(first).splitlines(keepends=True), str(second).splitlines(keepends=True),
                str(first), str(second),
                #fromfile = 'First',
                #tofile = 'Second',
            )
            diff = list(diff)
            #s = ''.join([
            #    '\nFirst:  ' + ''.join(difflib.restore(diff, 1)),
            #    '\nSecond: ' + ''.join(difflib.restore(diff, 2))])
            s = f'\nFirst:\n{first}\nSecond:\n{second}'
            self.fail(msg or s)


class TestTokenize(TestCase_NoDiff):
    def test_tokenize_0(self):
        cast = Ast('test', [TO(T.STRING, 'test', 0)])
        ast = Ast(cast.value)
        ast.tokenize_string_value()
        self.assertEqual(ast, cast)

    def test_tokenize_1(self):
        cast = Ast('(test)', [
            TO(T.LPAREN, '(', 1),
            TO(T.STRING, 'test', 1),
            TO(T.RPAREN, ')', 1)
        ])
        ast = Ast(cast.value)
        ast.tokenize_string_value()
        self.assertEqual(ast, cast)

    def test_tokenize_nest_0_1_0(self):
        cast = Ast('test[nest]test', [
            TO(T.STRING, 'test', 0),
            TO(T.LBRACKET, '[', 1),
            TO(T.STRING, 'nest', 1),
            TO(T.RBRACKET, ']', 1),
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.tokenize_string_value()
        self.assertEqual(ast, cast)

    def test_tokenize_nest_0_1_2_1_0(self):
        cast = Ast('test{nest(best)nest}test', [
            TO(T.STRING, 'test', 0),
            TO(T.LBRACE, '{', 1),
            TO(T.STRING, 'nest', 1),
            TO(T.LPAREN, '(', 2),
            TO(T.STRING, 'best', 2),
            TO(T.RPAREN, ')', 2),
            TO(T.STRING, 'nest', 1),
            TO(T.RBRACE, '}', 1),
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.tokenize_string_value()
        self.assertEqual(ast, cast)

    def test_tokenize_nest_0_1_2_1_0_1_2_1_0(self):
        cast = Ast('test{nest(best)nest}test[nest{best}nest]test', [
            TO(T.STRING, 'test', 0),
            TO(T.LBRACE, '{', 1),
            TO(T.STRING, 'nest', 1),
            TO(T.LPAREN, '(', 2),
            TO(T.STRING, 'best', 2),
            TO(T.RPAREN, ')', 2),
            TO(T.STRING, 'nest', 1),
            TO(T.RBRACE, '}', 1),
            TO(T.STRING, 'test', 0),
            TO(T.LBRACKET, '[', 1),
            TO(T.STRING, 'nest', 1),
            TO(T.LBRACE, '{', 2),
            TO(T.STRING, 'best', 2),
            TO(T.RBRACE, '}', 2),
            TO(T.STRING, 'nest', 1),
            TO(T.RBRACKET, ']', 1),
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.tokenize_string_value()
        self.assertEqual(ast, cast)

    def test_tokenize_nest_3(self):
        cast = Ast('([{test}])', [
            TO(T.LPAREN, '(', 1),
            TO(T.LBRACKET, '[', 2),
            TO(T.LBRACE, '{', 3),
            TO(T.STRING, 'test', 3),
            TO(T.RBRACE, '}', 3),
            TO(T.RBRACKET, ']', 2),
            TO(T.RPAREN, ')', 1)
        ])
        ast = Ast(cast.value)
        ast.tokenize_string_value()
        self.assertEqual(ast, cast)

class TestParse(TestCase_NoDiff):
    def test_parse_single_string(self):
        cast = Ast('test', [TO(T.STRING, 'test', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_int(self):
        cast = Ast('1', [TO(T.STRING, '1', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_int_radix(self):
        cast = Ast('0x01', [TO(T.STRING, '0x01', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_int_negative(self):
        cast = Ast('-1', [TO(T.STRING, '-1', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_int_positive(self):
        cast = Ast('+1', [TO(T.STRING, '+1', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_float(self):
        cast = Ast('0.1', [TO(T.STRING, '0.1', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_float_dot(self):
        cast = Ast('0.', [TO(T.STRING, '0.', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_dot_float(self):
        cast = Ast('.1', [TO(T.STRING, '.1', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_float_whole_exp(self):
        cast = Ast('1e-4', [TO(T.STRING, '1e-4', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_float_exp(self):
        cast = Ast('1.1e20', [TO(T.STRING, '1.1e20', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_bool(self):
        cast = Ast('True', [TO(T.STRING, 'True', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_bool_case(self):
        cast = Ast('fAlSe', [TO(T.STRING, 'fAlSe', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_bool_none(self):
        cast = Ast('None', [TO(T.STRING, 'None', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_bool_none_case(self):
        cast = Ast('none', [TO(T.STRING, 'none', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_qstring(self):
        cast = Ast("'none'", [TO(T.QSTRING, 'none', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_dqstring(self):
        cast = Ast('"none"', [TO(T.DQSTRING, 'none', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_single_dqstring_with_quoted_escapement(self):
        cast = Ast('"no\\"ne"', [TO(T.DQSTRING, 'no"ne', 0)])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_1(self):
        cast = Ast('(test)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.STRING, 'test', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_nest_0_1_0(self):
        cast = Ast('test[nest]test', [
            TO(T.STRING, 'test', 0), [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'nest', 1),
                TO(T.RBRACKET, ']', 1),
            ],
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_nest_0_1_2_1_0(self):
        cast = Ast('test{nest(best)nest}test', [
            TO(T.STRING, 'test', 0), [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'nest', 1), [
                    TO(T.LPAREN, '(', 2),
                    TO(T.STRING, 'best', 2),
                    TO(T.RPAREN, ')', 2),
                ],
                TO(T.STRING, 'nest', 1),
                TO(T.RBRACE, '}', 1),
            ],
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_nest_0_1_2_1_0_1_2_1_0(self):
        cast = Ast('test{nest(best)nest}test[nest{best}nest]test', [
            TO(T.STRING, 'test', 0), [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'nest', 1), [
                    TO(T.LPAREN, '(', 2),
                    TO(T.STRING, 'best', 2),
                    TO(T.RPAREN, ')', 2),
                ],
                TO(T.STRING, 'nest', 1),
                TO(T.RBRACE, '}', 1),
            ],
            TO(T.STRING, 'test', 0), [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'nest', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'best', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.STRING, 'nest', 1),
                TO(T.RBRACKET, ']', 1),
            ],
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

    def test_parse_nest_3(self):
        cast = Ast('([{test}])', [
            [
                TO(T.LPAREN, '(', 1), [
                    TO(T.LBRACKET, '[', 2), [
                        TO(T.LBRACE, '{', 3),
                        TO(T.STRING, 'test', 3),
                        TO(T.RBRACE, '}', 3),
                    ],
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.parse_tokenized_string_value()
        self.assertEqual(ast, cast)

class TestCondition(TestCase_NoDiff):
    def test_parse_0(self):
        cast = Ast('test', [TO(T.STRING, 'test', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_int(self):
        cast = Ast('1', [TO(T.INT, '1', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_int_radix(self):
        cast = Ast('0x01', [TO(T.INT, '0x01', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_int_negative(self):
        cast = Ast('-1', [TO(T.INT, '-1', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_int_positive(self):
        cast = Ast('+1', [TO(T.INT, '+1', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_float(self):
        cast = Ast('0.1', [TO(T.FLOAT, '0.1', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_float_dot(self):
        cast = Ast('0.', [TO(T.FLOAT, '0.', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_dot_float(self):
        cast = Ast('.1', [TO(T.FLOAT, '.1', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_float_whole_exp(self):
        cast = Ast('1e-4', [TO(T.FLOAT, '1e-4', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_float_exp(self):
        cast = Ast('1.1e20', [TO(T.FLOAT, '1.1e20', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_bool(self):
        cast = Ast('True', [TO(T.BOOL, 'True', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_bool_case(self):
        cast = Ast('fAlSe', [TO(T.BOOL, 'fAlSe', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_bool_none(self):
        cast = Ast('None', [TO(T.NONE, 'None', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_bool_none_case(self):
        cast = Ast('none', [TO(T.NONE, 'none', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_qstring(self):
        cast = Ast("'none'", [TO(T.QSTRING, 'none', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_dqstring(self):
        cast = Ast('"none"', [TO(T.DQSTRING, 'none', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_single_dqstring_with_quoted_escapement(self):
        cast = Ast('"no\\"ne"', [TO(T.DQSTRING, 'no"ne', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_1_braces(self):
        cast = Ast('{test}', [TO(T.STRING, '{test}', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_1_escaped_braces(self):
        cast = Ast('\\{test\\}', [TO(T.STRING, '{test}', 0)])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_1_int(self):
        cast = Ast('{1}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.INT, '1', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_1_float(self):
        cast = Ast('{6.28}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.FLOAT, '6.28', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_1_bool(self):
        cast = Ast('{true}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.BOOL, 'true', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_1_none(self):
        cast = Ast('{none}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.NONE, 'none', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_1_qstring(self):
        cast = Ast('{\'test\'}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.QSTRING, 'test', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_1_dqstring(self):
        cast = Ast('{"test"}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.DQSTRING, 'test', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_tuple_1_string(self):
        cast = Ast('(test)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.STRING, 'test', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_tuple_1_int(self):
        cast = Ast('(1)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.INT, '1', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_tuple_1_float(self):
        cast = Ast('(6.28)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.FLOAT, '6.28', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_tuple_1_bool(self):
        cast = Ast('(true)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.BOOL, 'true', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_tuple_1_none(self):
        cast = Ast('(none)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.NONE, 'none', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_tuple_1_qstring(self):
        cast = Ast('(\'test\')', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.QSTRING, 'test', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_tuple_1_dqstring(self):
        cast = Ast('("test")', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.DQSTRING, 'test', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_nest_0_1_0(self):
        cast = Ast('test[nest]test', [
            TO(T.STRING, 'test', 0), [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'nest', 1),
                TO(T.RBRACKET, ']', 1),
            ],
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_nest_0_1_2_1_0(self):
        cast = Ast('test{nest(best)nest}test', [
            TO(T.STRING, 'test', 0), [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'nest', 1), [
                    TO(T.LPAREN, '(', 2),
                    TO(T.STRING, 'best', 2),
                    TO(T.RPAREN, ')', 2),
                ],
                TO(T.STRING, 'nest', 1),
                TO(T.RBRACE, '}', 1),
            ],
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_nest_0_1_2_1_0_1_2_1_0(self):
        cast = Ast('test{nest(best)nest}test[nest{best}nest]test', [
            TO(T.STRING, 'test', 0), [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'nest', 1), [
                    TO(T.LPAREN, '(', 2),
                    TO(T.STRING, 'best', 2),
                    TO(T.RPAREN, ')', 2),
                ],
                TO(T.STRING, 'nest', 1),
                TO(T.RBRACE, '}', 1),
            ],
            TO(T.STRING, 'test', 0), [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'nest{best}nest', 1),
                TO(T.RBRACKET, ']', 1),
            ],
            TO(T.STRING, 'test', 0)
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_nest_3(self):
        cast = Ast('([{test}])', [
            [
                TO(T.LPAREN, '(', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, '{test}', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.RPAREN, ')', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_list_4_ns(self):
        cast = Ast('[a,b,c,d]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_list_4_ws(self):
        cast = Ast(' [a, b, c, d] ', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_list_1_2_1_ns(self):
        cast = Ast('[a,[b,c],d]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_list_3_1_ns(self):
        cast = Ast('[[a,b,c],d]', [
            [
                TO(T.LBRACKET, '[', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, 'a', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_list_1_3_ns(self):
        cast = Ast('[a,[b,c,d]]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.STRING, 'd', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_list_1_2_1_ws(self):
        cast = Ast('[a, [b, c], d]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_4_ns(self):
        cast = Ast('{a,b,c,d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_4_ws(self):
        cast = Ast('{a, b, c, d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_1_2_1_ns(self):
        cast = Ast('{a,{b,c},d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_set_1_2_1_ws(self):
        cast = Ast('{a, {b, c}, d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_dict_2_ns(self):
        cast = Ast('{a:b,c:d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1),
                TO(T.COLON, ':', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.COLON, ':', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_dict_2_ws(self):
        cast = Ast(' { a : b, c : d } ', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1),
                TO(T.COLON, ':', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.COLON, ':', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_dict_set_set_ns(self):
        cast = Ast('{{a,b}:{c,d}}', [
            [
                TO(T.LBRACE, '{', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'a', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                    TO(T.COLON, ':', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.STRING, 'd', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_dict_set_set_ws(self):
        cast = Ast('{ { a , b } : { c, d } }', [
            [
                TO(T.LBRACE, '{', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'a', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                    TO(T.COLON, ':', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.STRING, 'd', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_dict_dict_dict_ns(self):
        cast = Ast('{{a:b}:{c:d}}', [
            [
                TO(T.LBRACE, '{', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'a', 2),
                    TO(T.COLON, ':', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                    TO(T.COLON, ':', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.COLON, ':', 2),
                    TO(T.STRING, 'd', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

    def test_parse_dict_dict_dict_ws(self):
        cast = Ast(' { { a : b } : { c : d } } ', [
            [
                TO(T.LBRACE, '{', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'a', 2),
                    TO(T.COLON, ':', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                    TO(T.COLON, ':', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.COLON, ':', 2),
                    TO(T.STRING, 'd', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.RBRACE, '}', 1)
            ]
        ])
        ast = Ast(cast.value)
        ast.condition_tokens()
        self.assertEqual(ast, cast)

class TestObjectify(TestCase_NoDiff):
    # TODO NEXT: Testing objectify values
    def test_objectify_0(self):
        cast = Ast('test', [TO(T.STRING, 'test', 0)])
        cobj = 'test'
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_int(self):
        cast = Ast('1', [TO(T.INT, '1', 0)])
        cobj = 1
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_int_radix(self):
        cast = Ast('0x01', [TO(T.INT, '0x01', 0)])
        cobj = 1
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_int_negative(self):
        cast = Ast('-1', [TO(T.INT, '-1', 0)])
        cobj = -1
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_int_positive(self):
        cast = Ast('+1', [TO(T.INT, '+1', 0)])
        cobj = 1
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_float(self):
        cast = Ast('0.5', [TO(T.FLOAT, '0.5', 0)])
        cobj = 0.5
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_float_dot(self):
        cast = Ast('0.', [TO(T.FLOAT, '0.', 0)])
        cobj = 0.0
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_dot_float(self):
        cast = Ast('.25', [TO(T.FLOAT, '.25', 0)])
        cobj = 0.25
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_float_whole_exp(self):
        cast = Ast('1e-4', [TO(T.FLOAT, '1e-4', 0)])
        cobj = 1e-4
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_float_exp(self):
        cast = Ast('1.1e20', [TO(T.FLOAT, '1.1e20', 0)])
        cobj = 1.1e20
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_bool(self):
        cast = Ast('True', [TO(T.BOOL, 'True', 0)])
        cobj = True
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_bool_case(self):
        cast = Ast('fAlSe', [TO(T.BOOL, 'False', 0)])
        cobj = False
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_bool_none(self):
        cast = Ast('None', [TO(T.NONE, 'None', 0)])
        cobj = None
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_bool_none_case(self):
        cast = Ast('none', [TO(T.NONE, 'none', 0)])
        cobj = None
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_qstring(self):
        cast = Ast("'none'", [TO(T.QSTRING, 'none', 0)])
        cobj = 'none'
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_dqstring(self):
        cast = Ast('"none"', [TO(T.DQSTRING, 'none', 0)])
        cobj = 'none'
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_single_dqstring_with_quoted_escapement(self):
        cast = Ast('"no\\"ne"', [TO(T.DQSTRING, 'no"ne', 0)])
        cobj = 'no"ne'
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_1_braces(self):
        cast = Ast('{test}', [TO(T.STRING, '{test}', 0)])
        cobj = '{test}'
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_1_escaped_braces(self):
        cast = Ast('\\{test\\}', [TO(T.STRING, '{test}', 0)])
        cobj = '{test}'
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_1_int(self):
        cast = Ast('{1}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.INT, '1', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset([1])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_1_float(self):
        cast = Ast('{6.28}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.FLOAT, '6.28', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset([6.28])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_1_bool(self):
        cast = Ast('{true}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.BOOL, 'true', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset([True])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_1_none(self):
        cast = Ast('{none}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.NONE, 'none', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset([None])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_1_qstring(self):
        cast = Ast('{\'test\'}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.QSTRING, 'test', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset(['test'])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_1_dqstring(self):
        cast = Ast('{"test"}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.DQSTRING, 'test', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset(['test'])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_tuple_1_string(self):
        cast = Ast('(test)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.STRING, 'test', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        cobj = ('test',)
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_tuple_1_int(self):
        cast = Ast('(1)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.INT, '1', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        cobj = (1,)
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_tuple_1_float(self):
        cast = Ast('(6.28)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.FLOAT, '6.28', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        cobj = (6.28,)
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_tuple_1_bool(self):
        cast = Ast('(true)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.BOOL, 'true', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        cobj = (True,)
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_tuple_1_none(self):
        cast = Ast('(none)', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.NONE, 'none', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        cobj = (None,)
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_tuple_1_qstring(self):
        cast = Ast('(\'test\')', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.QSTRING, 'test', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        cobj = ('test',)
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_tuple_1_dqstring(self):
        cast = Ast('("test")', [
            [
                TO(T.LPAREN, '(', 1),
                TO(T.DQSTRING, 'test', 1),
                TO(T.RPAREN, ')', 1)
            ]
        ])
        cobj = ('test',)
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_nest_0_1_0(self):
        cast = Ast('[nest]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'nest', 1),
                TO(T.RBRACKET, ']', 1),
            ],
        ])
        cobj = ['nest']
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_nest_0_1_2_1_0_1_2_1_0(self):
        cast = Ast('[nest{best}nest]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'nest{best}nest', 1),
                TO(T.RBRACKET, ']', 1),
            ],
        ])
        cobj = ['nest{best}nest']
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_nest_3(self):
        cast = Ast('([{test}])', [
            [
                TO(T.LPAREN, '(', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, '{test}', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.RPAREN, ')', 1)
            ]
        ])
        cobj = (['{test}'],)
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_list_4_ns(self):
        cast = Ast('[a,b,c,d]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        cobj = ['a', 'b', 'c', 'd']
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_list_4_ws(self):
        cast = Ast(' [a, b, c, d] ', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        cobj = ['a', 'b', 'c', 'd']
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_list_1_2_1_ns(self):
        cast = Ast('[a,[b,c],d]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        cobj = ['a', ['b', 'c'], 'd']
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_list_3_1_ns(self):
        cast = Ast('[[a,b,c],d]', [
            [
                TO(T.LBRACKET, '[', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, 'a', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        cobj = [['a', 'b', 'c'], 'd']
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_list_1_3_ns(self):
        cast = Ast('[a,[b,c,d]]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.STRING, 'd', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        cobj = ['a', ['b', 'c', 'd']]
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_list_1_2_1_ws(self):
        cast = Ast('[a, [b, c], d]', [
            [
                TO(T.LBRACKET, '[', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACKET, '[', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACKET, ']', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACKET, ']', 1)
            ]
        ])
        cobj = ['a', ['b', 'c'], 'd']
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_4_ns(self):
        cast = Ast('{a,b,c,d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset(['a', 'b', 'c', 'd'])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_4_ws(self):
        cast = Ast('{a, b, c, d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset(['a', 'b', 'c', 'd'])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_1_2_1_ns(self):
        cast = Ast('{a,{b,c},d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset(['a', frozenset(['b', 'c']), 'd'])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_set_1_2_1_ws(self):
        cast = Ast('{a, {b, c}, d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = frozenset(['a', frozenset(['b', 'c']), 'd'])
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_dict_2_ns(self):
        cast = Ast('{a:b,c:d}', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1),
                TO(T.COLON, ':', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.COLON, ':', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = {'a':'b', 'c':'d'}
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_dict_2_ws(self):
        cast = Ast(' { a : b, c : d } ', [
            [
                TO(T.LBRACE, '{', 1),
                TO(T.STRING, 'a', 1),
                TO(T.COLON, ':', 1),
                TO(T.STRING, 'b', 1),
                TO(T.STRING, 'c', 1),
                TO(T.COLON, ':', 1),
                TO(T.STRING, 'd', 1),
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = {'a':'b', 'c':'d'}
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)

    def test_objectify_dict_set_set_ws(self):
        cast = Ast('{ { a , b } : { c, d } }', [
            [
                TO(T.LBRACE, '{', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'a', 2),
                    TO(T.STRING, 'b', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                    TO(T.COLON, ':', 1), [
                    TO(T.LBRACE, '{', 2),
                    TO(T.STRING, 'c', 2),
                    TO(T.STRING, 'd', 2),
                    TO(T.RBRACE, '}', 2),
                ],
                TO(T.RBRACE, '}', 1)
            ]
        ])
        cobj = {frozenset(['a','b']): frozenset(['c','d'])}
        ast = Ast(cast.value)
        obj = ast.objectify()
        self.assertEqual(obj, cobj)
