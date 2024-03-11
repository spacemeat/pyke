''' Options class and friends.'''
# pylint: disable=too-many-boolean-expressions, too-many-branches
import copy
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Callable
from .utilities import (InvalidOptionValue, re_interp_option, InvalidOptionOperation,
    set_color as c)

class Token(Enum):
    ''' Encodes tokens found in override values parsed from a string. '''
    ANY = '?'
    QSTRING = '\''
    DQSTRING = '"'
    LPAREN = '('
    RPAREN = ')'
    LBRACKET = '['
    RBRACKET = ']'
    LBRACE = '{'
    RBRACE = '}'
    COLON = ':'
    COMMA = ','
    STRING = 'a'
    FLOAT = '.'
    INT = '0'
    BOOL = 'T'
    NONE = 'N'
    SPACE = ' '

    def __str__(self):
        return f"{c('token_type')}{self.name}{c('off')}"

    def __repr__(self):
        return str(self)

@dataclass
class TokenObj:
    ''' A token lexed from a string value. '''
    token: Token
    value: str
    depth: int

    def __str__(self):
        return (f"{c('token_type')}{self.token.name}{c('off')}"
                f" ({c('token_depth')}{self.depth}{c('off')})"
                f" {c('token_value')}{self.value}{c('off')}")
        #return f"TO(T.{self.token.name}, '{self.value}', {self.depth})"

    def __repr__(self):
        return str(self)

TokenList = list[TokenObj|list['TokenList']]

class Ast:
    ''' Represents an abstract syntax tree for the strin value given.'''
    def __init__(self, value: str, toks: list = None):
        self.value = value
        self.toks = toks or []

    def __str__(self):
        def str_ast(ast: list, depth: int = 0) -> str:
            ''' Debugging '''
            s = ''
            for branch in ast:
                if isinstance(branch, list):
                    s += str_ast(branch, depth + 1)
                else:
                    s += f'{" " * depth * 4}{branch}\n'
            return s

        return str_ast(self.toks, 0)

    def __eq__(self, other):
        if not isinstance(other, Ast):
            return NotImplemented
        return self.value == other.value and self.toks == other.toks

    def tokenize_string_value(self):
        '''
        Turns an option value (as passed from the command line, probably) into a list of Tokens
        suitable for parsing into an object.
        '''
        self.toks = []
        idx = 0
        depth = 0
        nesting_tokens = []
        while idx < len(self.value):
            cur = self.value[idx]
            match cur:
                case '\'' | '"':
                    if cur == '\'':
                        self.toks.append(TokenObj(Token.QSTRING, '', depth))
                    else:
                        self.toks.append(TokenObj(Token.DQSTRING, '', depth))
                    sidx = idx + 1
                    while sidx < len(self.value):
                        scur = self.value[sidx]
                        if scur == '\\':
                            sidx += 1
                            if sidx < len(self.value):
                                scur = self.value[sidx]
                                self.toks[-1].value = ''.join([self.toks[-1].value, scur])
                            else:
                                raise InvalidOptionValue(f'Option value {self.value} cannot end in '
                                                         'a bare escapement.')
                        elif scur == cur:
                            idx = sidx
                            break
                        else:
                            self.toks[-1].value = ''.join([self.toks[-1].value, scur])
                        sidx += 1
                case '(':
                    depth += 1
                    self.toks.append(TokenObj(Token.LPAREN, '(', depth))
                    nesting_tokens.append(Token.LPAREN)
                case ')':
                    self.toks.append(TokenObj(Token.RPAREN, ')', depth))
                    if len(nesting_tokens) == 0:
                        raise InvalidOptionValue(f'Extraneous ")" in option value {self.value}.')
                    if nesting_tokens[-1] != Token.LPAREN:
                        raise InvalidOptionValue(f'Mismatched "{nesting_tokens[-1].value}"'
                                                 f'in option value {self.value}.')
                    nesting_tokens.pop()
                    depth -= 1
                case '[':
                    depth += 1
                    self.toks.append(TokenObj(Token.LBRACKET, '[', depth))
                    nesting_tokens.append(Token.LBRACKET)
                case ']':
                    self.toks.append(TokenObj(Token.RBRACKET, ']', depth))
                    if len(nesting_tokens) == 0:
                        raise InvalidOptionValue(f'Extraneous "]" in option value {self.value}.')
                    if nesting_tokens[-1] != Token.LBRACKET:
                        raise InvalidOptionValue(f'Mismatched "{nesting_tokens[-1].value}"'
                                                 f'in option value {self.value}.')
                    nesting_tokens.pop()
                    depth -= 1
                case '{':
                    depth += 1
                    self.toks.append(TokenObj(Token.LBRACE, '{', depth))
                    nesting_tokens.append(Token.LBRACE)
                case '}':
                    self.toks.append(TokenObj(Token.RBRACE, '}', depth))
                    if len(nesting_tokens) == 0:
                        raise InvalidOptionValue(f'Extraneous "]" in option value {self.value}.')
                    if nesting_tokens[-1] != Token.LBRACE:
                        raise InvalidOptionValue(f'Mismatched "{nesting_tokens[-1].value}"'
                                                 f'in option value {self.value}.')
                    nesting_tokens.pop()
                    depth -= 1
                case ':': self.toks.append(TokenObj(Token.COLON, ':', depth))
                case ',': self.toks.append(TokenObj(Token.COMMA, ',', depth))
                case '\\':
                    idx += 1
                    if idx < len(self.value):
                        cur = self.value[idx]
                    else:
                        raise InvalidOptionValue(f'Option value {self.value} cannot end in a bare '
                                                 'escapement.')
                    if len(self.toks) > 0 and self.toks[-1].token == Token.STRING:
                        self.toks[-1].value = ''.join([self.toks[-1].value, cur])
                    else:
                        self.toks.append(TokenObj(Token.STRING, cur, depth))
                case _:
                    if re.match(r'\s', cur):
                        if len(self.toks) > 0 and self.toks[-1].token == Token.SPACE:
                            self.toks[-1].value = ''.join([self.toks[-1].value, cur])
                        else:
                            self.toks.append(TokenObj(Token.SPACE, cur, depth))
                    else:
                        if len(self.toks) > 0 and self.toks[-1].token == Token.STRING:
                            self.toks[-1].value = ''.join([self.toks[-1].value, cur])
                        else:
                            self.toks.append(TokenObj(Token.STRING, cur, depth))
            if depth < 0:
                raise InvalidOptionValue(f'Malformed option override string: {self.value}')

            idx += 1

        if depth != 0:
            raise InvalidOptionValue(f'Malformed option override string: {self.value}')

        print (f'Tokenized:\n{self}')

    def parse_tokenized_string_value(self):
        '''
        Takes the inital token list, and transforms it into a nested list of lists to match
        the depth of collection elements recursively.
        '''
        self.tokenize_string_value()

        tok_idx = 0
        def recur(depth):
            nonlocal tok_idx
            ast = []
            while tok_idx < len(self.toks):
                if self.toks[tok_idx].depth > depth:
                    ast.append(recur(depth + 1))
                elif self.toks[tok_idx].depth < depth:
                    return ast
                else:
                    ast.append(self.toks[tok_idx])
                    tok_idx += 1
            return ast
        self.toks = recur(0)

        print (f'Parsed:\n{self}')

    def condition_tokens(self):
        '''
        Does various transforms on the token list to normalize it for object detection and
        construction.
        '''
        self.parse_tokenized_string_value()

        #   parse string tokens into other unit types
        #   turn {;a;} into <a> -- can be nested
        #   turn a;<b>;c into <abc>
        #   remove SPACEs everywhere?
        #   turn ?;:;? into <?:?>
        #   remove COMMAs everywhere?

        def get_num_tokens(ast: TokenList) -> int:
            num_tok = 0
            for obj in ast:
                if isinstance(obj, list):
                    num_tok += get_num_tokens(obj)
                else:
                    num_tok += 1
            return num_tok

        def recur_match(ast: TokenList, pattern: list[Token], then_what: Callable) -> TokenList:
            print (f'  Matching {pattern}...')
            tok_idx = 0
            while tok_idx < len(ast):
                tok = ast[tok_idx]
                if isinstance(tok, list):
                    the_what = recur_match(tok, pattern, then_what)
                    if len(the_what) > 1:
                        the_what = [the_what]
                    ast = (ast[:tok_idx]
                        + the_what
                        + ast[tok_idx + 1:])
                else:
                    match = True
                    for i, pattern_token in enumerate(pattern):
                        if (len(ast) <= tok_idx + i or
                            not isinstance(ast[tok_idx + i], TokenObj) or
                            pattern_token not in [ast[tok_idx + i].token, Token.ANY]):
                            match = False
                            break
                    if match:
                        the_what = then_what(ast[tok_idx:tok_idx + len(pattern)]) or []
                        ast = (ast[:tok_idx]
                            + the_what
                            + ast[tok_idx + len(pattern):])
                tok_idx += 1
            return ast

        def replace_string_with_unit(subtree: TokenList) -> TokenList:
            subtree = subtree[0]
            v = subtree.value
            if v == '0x01':
                breakpoint()
            try:
                int(v, 0)
                return [TokenObj(Token.INT, v, subtree.depth)]
            except OverflowError as exc:
                raise InvalidOptionValue(f'Int overflowed in value {v}') from exc
            except ValueError:
                pass
            try:
                float(v)
                return [TokenObj(Token.FLOAT, v, subtree.depth)]
            except OverflowError as exc:
                raise InvalidOptionValue(f'Float overflowed in value {v}') from exc
            except ValueError:
                pass
            if v.lower() in ["true", "false"]:
                return [TokenObj(Token.BOOL, v, subtree.depth)]
            if v.lower() == "none":
                return [TokenObj(Token.NONE, v, subtree.depth)]
            return [subtree]

        def replace_interpolated_string(subtree: list) -> list:
            return [TokenObj(Token.STRING, ''.join(['{', subtree[1].value, '}']),
                            subtree[1].depth - 1)]

        def replace_adjacent_strings(subtree: list) -> list:
            return [TokenObj(Token.STRING, ''.join([subtree[0].value, subtree[1].value]),
                            subtree[0].depth)]

        def remove_it(_:list) -> list:
            return []

        def replace_kvp(subtree:list) -> list:
            return [[TokenObj(st.token, st.value, st.depth + 1) for st in subtree]]

        ast = recur_match(self.toks, [Token.STRING], replace_string_with_unit)
        new_num_toks = get_num_tokens(ast)
        num_toks = new_num_toks + 1
        while new_num_toks < num_toks:
            num_toks = new_num_toks
            ast = recur_match(ast, [Token.LBRACE, Token.STRING, Token.RBRACE],
                              replace_interpolated_string)
            ast = recur_match(ast, [Token.STRING, Token.STRING],
                              replace_adjacent_strings)
            new_num_toks = get_num_tokens(ast)
        ast = recur_match(ast, [Token.SPACE], remove_it)
        ast = recur_match(ast, [Token.ANY, Token.COLON, Token.ANY], replace_kvp)
        ast = recur_match(ast, [Token.COMMA], remove_it)

        self.toks = ast

        print (f'Conditioned:\n{self}')

def parse_value(value: str):
    ''' Turn a value string into a value object. '''
    ast = Ast(value)
    ast.condition_tokens()

    return value

class OptionOp(Enum):
    ''' The operations you can perform with option overrides.'''
    REPLACE = '='
    APPEND = '+'    # append to lists/tuples, add to sets, union to dicts
    EXTEND = '*'    # extend to lists/tuples
    REMOVE = '-'    # remove by index from lists/tuples, by key from sets and dicts
    UNION = '|'     # union of sets and dicts
    INTERSECT = '&'     # intersection of sets
    DIFF = '~'    # difference of sets
    SYM_DIFF = '^' # sym_diff of sets


class Option:
    ''' Represents a named option. Stores all its overrides.'''
    def __init__(self, name: str, value):
        self.name = name
        self.value = []
        self.value.append((value, OptionOp.REPLACE))

    def push_value_op(self, value, op: OptionOp = OptionOp.REPLACE):
        ''' Sets a value to this Option, as an override to previous values. '''
        self.value.append((value, op))

    def pop_value_op(self):
        ''' Removes the last override.'''
        del self.value[-1]

class Options:
    '''
    phase.opts |= {'foo_b': True}
    phase.opts |= {'foo_s': 'bar'}
    phase.opts |= {'foo_lb': ['bar', False]}
    phase.opts |= {'foo_ls': ['bar', 'baz']}
    phase.opts |= {'foo_db': {'bar': True, 'sna': False}
    phase.opts |= {'foo_ds': {'bar': 'baz', 'sna': 'guh'}
    ...
    phase.opts |= {'foo_b': False}                  # overrides the value
    phase.opts |= {'foo_ls: ['fleeb', 'plugh']}     # overrides the whole list
    phase.opts |= {'foo_ls+: ['fleeb', 'plugh']}    # appends to the list
    phase.opts |= {'foo_ls-: ['bar']}               # removes 'bar' from the list
    phase.opts |= {'foo_db': {'sna': True}}         # overrides the whole dict
    phase.opts |= {'foo_db+': {'sna': True}}        # overrides the dict value
    phase.opts |= {'foo_db+': {'zin': True}}        # appends the dict value
    phase.opts |= {'foo_db-': {'sna'}}              # removes the dict value

    -o foo_ds:{bar:baz}
    -o kvs:{url:{ht_method}://foo.com,user:$REDIS_ID,password:$REDIS_PWD}
    '''
    def __init__(self):
        self.opts = {}

    def __ior__(self, new_opts):
        for k, v in new_opts.items():
            self.push(k, v, OptionOp.REPLACE)
        return self

    def __iter__(self):
        ''' Iterates over the options.'''
        return iter(self.opts.items())

    def iter(self):
        ''' Returns an iterator over the options.'''
        return self.opts.items()

    def clone(self):
        ''' Return a deep copy of this options object.'''
        return copy.deepcopy(self)

    def keys(self):
        ''' Returns the option keys.'''
        return self.opts.keys()

    def push(self, k, v, op=None):
        ''' Push an option override.'''
        if op is None:
            op = OptionOp.REPLACE
            for eop in OptionOp:
                if k[-1] == eop.value:
                    op = eop

        v = parse_value(v)

        if k not in self.opts:
            self.opts[k] = Option(k, v)
        else:
            self.opts[k].push_value_op(v, op)

    def pop(self, key):
        ''' Pop the latest option override.'''
        self.opts[key].pop_value_op()

    def get(self, key, interpolate=True):
        ''' Get the ultimate value of the option.'''
        opt = self.opts[key]
        values = copy.deepcopy(opt.value)
        if not interpolate:
            return values

        def interp(v):
            val = v
            while isinstance(val, str):
                m = re_interp_option.search(val, 0)
                if m is None:
                    return val
                if m.start() > 0 or m.end() < len(val):
                    lookup = self.get(interp(m.group(1)))
                    val = val[:m.start()] + str(lookup) + val[m.end():]
                    continue
                val = self.get(interp(m.group(1)))

            if isinstance(val, list):
                val = [interp(ve) for ve in val]
                return val

            if isinstance(val, tuple):
                val = (interp(ve) for ve in val)
                return val

            if isinstance(val, set):
                new_val = set()
                for vv in val:
                    vv = interp(vv)
                    new_val.add(vv)
                return new_val

            if isinstance(val, dict):
                new_val = {}
                for vk, vv in val.items():
                    vk = interp(vk)
                    vv = interp(vv)
                    new_val[vk] = vv
                return new_val

            return val

        values = [(interp(v), op) for v, op in values]

        # now merge them according to ops
        computed, _ = values[0]
        for val in values[1:]:
            override, op = val
            computed = self._apply_op(computed, override, op)

        return computed

    def _apply_op(self, computed, override, op):
        if op == OptionOp.REPLACE:
            return override
        
        if isinstance(computed, list):
            if op == OptionOp.APPEND:
                return [*computed, override]
            if op == OptionOp.EXTEND:
                if isinstance(override, (list, tuple)):
                    return [*computed, *override]
            if op == OptionOp.REMOVE:
                if isinstance(override, int):
                    return [e for i, e in enumerate(computed) if i != override]
                if isinstance(override, (list, tuple)):
                    if all((isinstance(e, int) for e in override)):
                        return [e for i, e in enumerate(computed) if i not in override]
                raise InvalidOptionOperation('Remove from list operands must be by integer index.')

        if isinstance(computed, tuple):
            if op == OptionOp.APPEND:
                return (*computed, override)
            if op == OptionOp.EXTEND:
                if isinstance(override, (list, tuple)):
                    return (*computed, *override)
            if op == OptionOp.REMOVE:
                if isinstance(override, int):
                    return (e for i, e in enumerate(computed) if i != override)
                if isinstance(override, (list, tuple)):
                    if all((isinstance(e, int) for e in override)):
                        return (e for i, e in enumerate(computed) if i not in override)
                raise InvalidOptionOperation('Remove from tuple operands must be by integer index.')

        if isinstance(computed, set):
            if op == OptionOp.APPEND:
                return {*computed, override}
            if op == OptionOp.REMOVE:
                return computed - {override}
            if op == OptionOp.UNION:
                if isinstance(override, set):
                    return computed | override
                raise InvalidOptionOperation('Union operands must be sets.')
            if op == OptionOp.INTERSECT:
                if isinstance(override, set):
                    return computed & override
                raise InvalidOptionOperation('Intersect operands must be sets.')
            if op == OptionOp.DIFF:
                if isinstance(override, set):
                    return computed - override
                raise InvalidOptionOperation('Difference operands must be sets.')
            if op == OptionOp.SYM_DIFF:
                if isinstance(override, set):
                    return computed ^ override
                raise InvalidOptionOperation('Symmetric difference operands must be sets.')

        if isinstance(computed, dict):
            if op == OptionOp.APPEND or op == OptionOp.UNION:
                if not isinstance(override, dict):
                    raise InvalidOptionOperation('Append/union operands to dicts must be dicts.')
                return computed | override
            if op == OptionOp.REMOVE:
                if isinstance(override, str):
                    return {k: v for k, v in computed.items() if k != override}
                if isinstance(override, (list, tuple, set)):
                    if all((isinstance(e, str) for e in override)):
                        return {k: v for k, v, in computed.items() if k not in override}
                raise InvalidOptionOperation('Remove operands from dicts must be lists, tuples, or sets.')

        if op != OptionOp.REPLACE:
            raise InvalidOptionOperation('Override operators cannot be applied to this option'
                                         f'of type {type(computed)}.')
        return override



if __name__ == '__main__':
    opts = Options()
    opts |= {
        'foo': 'bar',
        'baz': ['foo', '{foo}', 'abc{foo}def'],
        'sna': '{baz}',
        'cat': { 'dog': 'ray', 'cow': {'pig': 'bug', 'ant':'bee'} },
        'gar': ['bun', '--{cat}--', '{sna}'],
        'gnu': ['zip', 'one', 'two', 'thr'],
        'fly': [0, 2],
    }

    def p(k):
        print (f'{k}: {opts.get(k)}')

    p('foo')
    p('sna')
    p('cat')
    p('gar')
    p('gnu')
    opts.push('baz+', 'add0')
    opts.push('baz+', ['add1', 'add2'])
    opts.push('baz-', 1)
    opts.push('gnu-', '{fly}')
    p('foo')
    p('sna')
    p('cat')
    p('gar')
    p('gnu')
    opts.pop('gnu')
    opts.pop('baz')
    opts.pop('baz')
    opts.pop('baz')
    p('foo')
    p('sna')
    p('cat')
    p('gar')
    p('gnu')
