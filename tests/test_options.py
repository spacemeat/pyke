''' Unit test for options module. '''

#pylint: disable=missing-class-docstring, missing-function-docstring
#pylint: disable=too-many-public-methods, too-many-lines

import unittest
from pyke.options import Options, OptionOp, Op
from pyke.utilities import InvalidOptionOperation

class TestOperators(unittest.TestCase):
    def setUp(self):
        self.initial_values = {
            'bool': True,
            'int': 2,
            'float': 6.28,
            'stra': 'a',
            'strb': 'b',
            'string': 'abracadabra',
            'list_of_string': ['{stra}', 'b', 'c'],
            'list_of_int': [0, 1, '{int}', 3],
            'tuple_of_string': ('a', '{strb}', 'c'),
            'tuple_of_int': (0, 1, '{int}', 3),
            'tuple_of_any': (0, 'a', {'b': 'c'}),
            'set_of_string': {'a', 'b', 'c'},
            'set_of_int': {0, 1, '{int}', 3},
            'set_of_any': {0, 'a', ('b', 1, 2)},
            'dict_of_string': {'a': 'b', 'c': 'd', 'e': 'f'},
            'dict_of_dict': {'a': {'b': 'c', 'd': 'e'}, 'f': {'g': 'h', 'i': 'j'}},
        }

        self.options = Options()
        self.options |= self.initial_values

    def ensure_val(self, option, expected):
        actual = self.options.get(option)
        self.assertEqual(actual, expected)

    def test_get_bool(self):
        self.ensure_val('bool', True)

    def test_get_int(self):
        self.ensure_val('int', 2)

    def test_get_float(self):
        self.ensure_val('float', 6.28)

    def test_get_string(self):
        self.ensure_val('string', 'abracadabra')

    def test_get_list(self):
        self.ensure_val('list_of_string', ['a', 'b', 'c'])

    def test_get_tuple(self):
        self.ensure_val('tuple_of_string', ('a', 'b', 'c'))

    def test_get_set(self):
        self.ensure_val('set_of_int', {0, 1, 2, 3})

    def test_get_dict(self):
        self.ensure_val('dict_of_string', {'a': 'b', 'c': 'd', 'e': 'f'})

    def ensure_override(self, option, op, value, expected):
        self.options.push(option, Op(op, value))
        actual = self.options.get(option)
        self.assertEqual(actual, expected)

    def test_replace_bool(self):
        self.ensure_override('bool', OptionOp.REPLACE, False, False)

    def test_replace_int(self):
        self.ensure_override('int', OptionOp.REPLACE, 3, 3)

    def test_replace_float(self):
        self.ensure_override('float', OptionOp.REPLACE, 2.718, 2.718)

    def test_replace_string(self):
        self.ensure_override('string', OptionOp.REPLACE, 'hocus pocus', 'hocus pocus')

    def test_replace_list(self):
        self.ensure_override('list_of_string', OptionOp.REPLACE, ['foo', 'bar'], ['foo', 'bar'])

    def test_replace_tuple(self):
        self.ensure_override('tuple_of_string', OptionOp.REPLACE, ('foo', 'bar'), ('foo', 'bar'))

    def test_replace_set(self):
        self.ensure_override('set_of_int', OptionOp.REPLACE, {2, 3, 5, 7}, {2, 3, 5, 7})

    def test_replace_dict(self):
        self.ensure_override('dict_of_string', OptionOp.REPLACE,
                              {'ding': 'dong'}, {'ding': 'dong'})

    def test_math_int_add(self):
        self.ensure_override('int', OptionOp.ADD, 3, 5)

    def test_math_int_subtract(self):
        self.ensure_override('int', OptionOp.SUBTRACT, 3, -1)

    def test_math_int_multiply(self):
        self.ensure_override('int', OptionOp.MULTIPLY, 3, 6)

    def test_math_int_divide(self):
        self.ensure_override('int', OptionOp.DIVIDE, 3, 2/3)

    def test_math_float_add(self):
        self.ensure_override('float', OptionOp.ADD, 3, 6.28 + 3)

    def test_math_float_subtract(self):
        self.ensure_override('float', OptionOp.SUBTRACT, 3, 6.28 - 3)

    def test_math_float_multiply(self):
        self.ensure_override('float', OptionOp.MULTIPLY, 3, 6.28 * 3)

    def test_math_float_divide(self):
        self.ensure_override('float', OptionOp.DIVIDE, 3, 6.28 / 3)

    def test_string_add(self):
        self.ensure_override('string', OptionOp.ADD, 'bobabra', 'abracadabrabobabra')

    def test_string_add_interp(self):
        self.ensure_override('string', OptionOp.ADD, '{strb}', 'abracadabrab')

    def test_string_subtract(self):
        self.ensure_override('string', OptionOp.SUBTRACT, 'abra', 'cadabra')

    def test_string_subtract_missing(self):
        self.ensure_override('string', OptionOp.SUBTRACT, 'abrae', 'abracadabra')

    def test_list_append_str(self):
        self.ensure_override('list_of_string', OptionOp.APPEND, 'd', ['a', 'b', 'c', 'd'])

    def test_list_append_empty_list(self):
        self.ensure_override('list_of_string', OptionOp.APPEND, [], ['a', 'b', 'c', []])

    def test_list_append_none(self):
        self.ensure_override('list_of_string', OptionOp.APPEND, None, ['a', 'b', 'c', None])

    def test_list_append_empty_str(self):
        self.ensure_override('list_of_string', OptionOp.APPEND, '', ['a', 'b', 'c', ''])

    def test_list_extend_list(self):
        self.ensure_override('list_of_string', OptionOp.EXTEND,
                             ['d', 'e'], ['a', 'b', 'c', 'd', 'e'])

    def test_list_extend_list_of_list(self):
        self.ensure_override('list_of_string', OptionOp.EXTEND,
                             [['d', 'e']], ['a', 'b', 'c', ['d', 'e']])

    def test_list_extend_empty_list(self):
        self.ensure_override('list_of_string', OptionOp.EXTEND, [], ['a', 'b', 'c'])

    def test_list_extend_string(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('list_of_string', OptionOp.EXTEND, 'd', None)

    def test_list_extend_tuple(self):
        self.ensure_override('list_of_string', OptionOp.EXTEND,
                             ('d', 'e'), ['a', 'b', 'c', 'd', 'e'])

    def test_list_extend_tuple_of_list(self):
        self.ensure_override('list_of_string', OptionOp.EXTEND,
                             (['d', 'e'],), ['a', 'b', 'c', ['d', 'e']])

    def test_list_extend_empty_tuple(self):
        self.ensure_override('list_of_string', OptionOp.EXTEND, tuple(), ['a', 'b', 'c'])

    def test_list_remove_str(self):
        self.ensure_override('list_of_string', OptionOp.REMOVE, 'a', ['b', 'c'])

    def test_list_remove_list_of_list(self):
        self.ensure_override('list_of_string', OptionOp.EXTEND,
                             [['d', 'e']], ['a', 'b', 'c', ['d', 'e']])
        self.ensure_override('list_of_string', OptionOp.REMOVE, ['d', 'e'], ['a', 'b', 'c'])

    def test_list_remove_missing(self):
        self.ensure_override('list_of_string', OptionOp.REMOVE, 'e', ['a', 'b', 'c'])

    def test_list_diff_single_idx(self):
        self.ensure_override('list_of_string', OptionOp.DIFF, 0, ['b', 'c'])

    def test_list_diff_list_of_idx(self):
        self.ensure_override('list_of_string', OptionOp.DIFF, [0, 2], ['b'])

    def test_list_diff_list_of_idx_reverse(self):
        self.ensure_override('list_of_string', OptionOp.DIFF, [2, 0], ['b'])

    def test_list_diff_tuple_of_idx(self):
        self.ensure_override('list_of_string', OptionOp.DIFF, (0, 2), ['b'])

    def test_list_diff_tuple_of_idx_reverse(self):
        self.ensure_override('list_of_string', OptionOp.DIFF, (2, 0), ['b'])

    def test_list_diff_set_of_idx(self):
        self.ensure_override('list_of_string', OptionOp.DIFF, {0, 2}, ['b'])

    def test_list_diff_set_of_idx_reverse(self):
        self.ensure_override('list_of_string', OptionOp.DIFF, {2, 0}, ['b'])

    def test_list_diff_not_int(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('list_of_string', OptionOp.DIFF, 'a', None)

    def test_list_diff_not_int_in_list(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('list_of_string', OptionOp.DIFF, [0, 'a'], None)

    def test_list_diff_bad_op(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('list_of_string', OptionOp.UNION, ['d'], None)


    def test_tuple_append_str(self):
        self.ensure_override('tuple_of_string', OptionOp.APPEND, 'd', ('a', 'b', 'c', 'd'))

    def test_tuple_append_empty_list(self):
        self.ensure_override('tuple_of_string', OptionOp.APPEND, [], ('a', 'b', 'c', []))

    def test_tuple_append_none(self):
        self.ensure_override('tuple_of_string', OptionOp.APPEND, None, ('a', 'b', 'c', None))

    def test_tuple_append_empty_str(self):
        self.ensure_override('tuple_of_string', OptionOp.APPEND, '', ('a', 'b', 'c', ''))

    def test_tuple_extend_list(self):
        self.ensure_override('tuple_of_string', OptionOp.EXTEND,
                             ['d', 'e'], ('a', 'b', 'c', 'd', 'e'))

    def test_tuple_extend_list_of_list(self):
        self.ensure_override('tuple_of_string', OptionOp.EXTEND,
                             [['d', 'e']], ('a', 'b', 'c', ['d', 'e']))

    def test_tuple_extend_empty_list(self):
        self.ensure_override('tuple_of_string', OptionOp.EXTEND, [], ('a', 'b', 'c'))

    def test_tuple_extend_string(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('tuple_of_string', OptionOp.EXTEND, 'd', None)

    def test_tuple_extend_tuple(self):
        self.ensure_override('tuple_of_string', OptionOp.EXTEND,
                             ('d', 'e'), ('a', 'b', 'c', 'd', 'e'))

    def test_tuple_extend_tuple_of_list(self):
        self.ensure_override('tuple_of_string', OptionOp.EXTEND,
                             (['d', 'e'],), ('a', 'b', 'c', ['d', 'e']))

    def test_tuple_extend_empty_tuple(self):
        self.ensure_override('tuple_of_string', OptionOp.EXTEND, tuple(), ('a', 'b', 'c'))

    def test_tuple_remove_str(self):
        self.ensure_override('tuple_of_string', OptionOp.REMOVE, 'a', ('b', 'c'))

    def test_tuple_remove_list_of_list(self):
        self.ensure_override('tuple_of_string', OptionOp.EXTEND,
                             (['d', 'e'],), ('a', 'b', 'c', ['d', 'e']))
        self.ensure_override('tuple_of_string', OptionOp.REMOVE, ['d', 'e'], ('a', 'b', 'c'))

    def test_tuple_remove_missing(self):
        self.ensure_override('tuple_of_string', OptionOp.REMOVE, 'e', ('a', 'b', 'c'))

    def test_tuple_diff_single_idx(self):
        self.ensure_override('tuple_of_string', OptionOp.DIFF, 0, ('b', 'c'))

    def test_tuple_diff_list_of_idx(self):
        self.ensure_override('tuple_of_string', OptionOp.DIFF, [0, 2], ('b',))

    def test_tuple_diff_list_of_idx_reverse(self):
        self.ensure_override('tuple_of_string', OptionOp.DIFF, [2, 0], ('b',))

    def test_tuple_diff_tuple_of_idx(self):
        self.ensure_override('tuple_of_string', OptionOp.DIFF, (0, 2), ('b',))

    def test_tuple_diff_tuple_of_idx_reverse(self):
        self.ensure_override('tuple_of_string', OptionOp.DIFF, (2, 0), ('b',))

    def test_tuple_diff_set_of_idx(self):
        self.ensure_override('tuple_of_string', OptionOp.DIFF, {0, 2}, ('b',))

    def test_tuple_diff_set_of_idx_reverse(self):
        self.ensure_override('tuple_of_string', OptionOp.DIFF, {2, 0}, ('b',))

    def test_tuple_diff_not_int(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('tuple_of_string', OptionOp.DIFF, 'a', None)

    def test_tuple_diff_not_int_in_list(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('tuple_of_string', OptionOp.DIFF, [0, 'a'], None)

    def test_tuple_diff_bad_op(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('tuple_of_string', OptionOp.UNION, ['d'], None)

    def test_set_append(self):
        self.ensure_override('set_of_string', OptionOp.APPEND, 'd', {'a', 'b', 'c', 'd'})

    def test_set_append_none(self):
        self.ensure_override('set_of_string', OptionOp.APPEND, None, {'a', 'b', 'c', None})

    def test_set_remove(self):
        self.ensure_override('set_of_string', OptionOp.REMOVE, 'a', {'b', 'c'})

    def test_set_remove_tuple(self):
        self.ensure_override('set_of_string', OptionOp.APPEND,
                             ('d', 'e'), {'a', 'b', 'c', ('d', 'e')})
        self.ensure_override('set_of_string', OptionOp.REMOVE, ('d', 'e'), {'a', 'b', 'c'})

    def test_set_remove_missing(self):
        self.ensure_override('set_of_string', OptionOp.REMOVE, 'd', {'a', 'b', 'c'})

    def test_set_union(self):
        self.ensure_override('set_of_string', OptionOp.UNION,
                             {'c', 'd', 'e'}, {'a', 'b', 'c', 'd', 'e'})

    def test_set_union_non_set(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('set_of_string', OptionOp.UNION,
                                 ['c', 'd', 'e'], None)

    def test_set_intersect(self):
        self.ensure_override('set_of_string', OptionOp.INTERSECT,
                             {'c', 'd', 'e'}, {'c'})

    def test_set_intersect_non_set(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('set_of_string', OptionOp.INTERSECT,
                                 ['c', 'd', 'e'], None)

    def test_set_diff(self):
        self.ensure_override('set_of_string', OptionOp.DIFF,
                             {'c', 'd', 'e'}, {'a', 'b'})

    def test_set_diff_non_set(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('set_of_string', OptionOp.DIFF,
                                 ['c', 'd', 'e'], None)

    def test_set_symmetric_diff(self):
        self.ensure_override('set_of_string', OptionOp.SYM_DIFF,
                             {'c', 'd', 'e'}, {'a', 'b', 'd', 'e'})

    def test_set_symmetric_diff_non_set(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('set_of_string', OptionOp.SYM_DIFF,
                                 ['c', 'd', 'e'], None)

    def test_dict_append(self):
        self.ensure_override('dict_of_string', OptionOp.APPEND,
                             {'g': 'h'}, {'a': 'b', 'c':'d', 'e':'f', 'g':'h'})

    def test_dict_append_non_dict(self):
        with self.assertRaises(InvalidOptionOperation):
            self.ensure_override('dict_of_string', OptionOp.APPEND,
                                 ['g', 'h'], None)

    def test_dict_append_value_replace(self):
        self.ensure_override('dict_of_string', OptionOp.APPEND,
                             {'a': 'h'}, {'a': 'h', 'c':'d', 'e':'f'})

    def test_dict_remove_list(self):
        self.ensure_override('dict_of_string', OptionOp.REMOVE,
                             ['a', 'e'], {'c': 'd'})

    def test_dict_remove(self):
        self.ensure_override('dict_of_string', OptionOp.REMOVE,
                             'a', {'c': 'd', 'e': 'f'})
