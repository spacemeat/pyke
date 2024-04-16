''' Bits for parsing stringized options, like one gets from a command line.'''

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Callable
from .utilities import InvalidOptionValue

class Token(Enum):
    ''' Encodes tokens found in override values parsed from a string. '''
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
    SPACE = ' '

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return str(self)

@dataclass
class TokenObj:
    ''' A token lexed from a string value. '''
    token: Token
    value: str
    depth: int

    def __str__(self):
        return f'{self.token.name} ({self.depth}): {self.value}'

    def __repr__(self):
        return str(self)

TokenList = list[TokenObj|list['TokenList']]

class Ast:
    ''' Represents an abstract syntax tree for the string value given.'''
    def __init__(self, value: str, toks: list | None = None):
        self.value = value
        self.toks: list = toks or []

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
        ''' Turns an option value (as passed from the command line, probably) into a list of Tokens
        suitable for parsing into an object. '''
        self.toks = []
        idx = 0
        depth = 0
        nesting_tokens = []

        if self.value == '':
            self.toks.append(TokenObj(Token.STRING, '', depth))
        else:
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
                                    raise InvalidOptionValue(
                                        f'Option value {self.value} cannot end in a bare '
                                        'escapement.')
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
                            raise InvalidOptionValue(
                                'Extraneous ")" in option value {self.value}.')
                        if nesting_tokens[-1] != Token.LPAREN:
                            raise InvalidOptionValue(
                                f'Mismatched "{nesting_tokens[-1].value}" in option value '
                                f'{self.value}.')
                        nesting_tokens.pop()
                        depth -= 1
                    case '[':
                        depth += 1
                        self.toks.append(TokenObj(Token.LBRACKET, '[', depth))
                        nesting_tokens.append(Token.LBRACKET)
                    case ']':
                        self.toks.append(TokenObj(Token.RBRACKET, ']', depth))
                        if len(nesting_tokens) == 0:
                            raise InvalidOptionValue(
                                f'Extraneous "]" in option value {self.value}.')
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
                            raise InvalidOptionValue(
                                f'Extraneous "]" in option value {self.value}.')
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
                            raise InvalidOptionValue(
                                f'Option value {self.value} cannot end in a bare escapement.')
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

    def condition_tokens(self):
        ''' Does various transforms on the token list to normalize it for object detection and
        construction. '''
        self.parse_tokenized_string_value()

        #   parse string tokens into other unit types
        #   turn {;a;} into <a> -- can be nested
        #   turn a;<b>;c into <abc>
        #   remove SPACEs everywhere?
        #   turn ?;:;? into <?:?>
        #   remove COMMAs everywhere?

        def get_num_tokens(ast: list) -> int:
            num_tok = 0
            for obj in ast:
                if isinstance(obj, list):
                    num_tok += get_num_tokens(obj)
                else:
                    num_tok += 1
            return num_tok

        def inc_depth(ast: list) -> list:
            for obj in ast:
                if isinstance(obj, list):
                    inc_depth(obj)
                else:
                    obj.depth += 1
            return ast

        def recur_match(ast: list, pattern: list[Token], then_what: Callable) -> list:
            tok_idx = 0
            new_ast = []
            while tok_idx < len(ast):
                tok = ast[tok_idx]
                if isinstance(tok, list):
                    the_what = recur_match(tok, pattern, then_what)
                    if len(the_what) > 1:
                        the_what = [the_what]
                    new_ast.extend(the_what)

                else:
                    match = True
                    for i, pattern_token in enumerate(pattern):
                        if (len(ast) <= tok_idx + i or                 # pattern is too long
                            isinstance(ast[tok_idx + i], list) or      # pattern can't match a list
                            pattern_token != ast[tok_idx + i].token):  # pattern doesn't match token
                            match = False
                            break

                    if match:
                        the_what = then_what(ast[tok_idx : tok_idx + len(pattern)])
                        tok_idx += len(pattern) - 1
                        new_ast.extend(the_what)
                    else:
                        new_ast.append(tok)

                tok_idx += 1
            return new_ast

        def replace_string_with_unit(subtree: list) -> list:
            subtree = subtree[0]
            assert isinstance(subtree, TokenObj)
            v = subtree.value
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
            return [subtree]

        def replace_interpolated_string(subtree: list) -> list:
            return [TokenObj(Token.STRING, ''.join(['{', subtree[1].value, '}']),
                            subtree[1].depth - 1)]

        def replace_adjacent_strings(subtree: list) -> list:
            return [TokenObj(Token.STRING, ''.join([subtree[0].value, subtree[1].value]),
                            subtree[0].depth)]

        def remove_it(_:list) -> list:
            return []

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
        ast = recur_match(ast, [Token.COMMA], remove_it)

        self.toks = ast

    def objectify(self):
        ''' Turns a conditioned value into objects. '''
        self.condition_tokens()

        def recur(toks: list) -> Any:
            tok_idx = 0

            def get_unit_obj(tok: TokenObj) -> Any:
                match tok.token:
                    case Token.INT: return int(tok.value, 0)
                    case Token.FLOAT: return float(tok.value)
                    case Token.QSTRING: return tok.value
                    case Token.DQSTRING: return tok.value
                    case Token.STRING: return tok.value
                return tok

            while tok_idx < len(toks):
                tok = toks[tok_idx]
                if isinstance(tok, list):
                    return recur(tok)

                if tok.token == Token.LBRACE:
                    is_dict = True
                    for i in range(tok_idx + 2, len(toks), 3):
                        if isinstance(toks[i], list) or toks[i].token != Token.COLON:
                            is_dict = False
                            break

                    if is_dict:
                        obj = {}
                        for i in range(tok_idx + 1, len(toks) - 2, 3):
                            k = toks[i]
                            v = toks[i + 2]
                            if isinstance(k, list):
                                k = recur(k)
                            else:
                                k = get_unit_obj(k)
                            if isinstance(v, list):
                                v = recur(v)
                            else:
                                v = get_unit_obj(v)
                            obj[k] = v
                        return obj

                    obj = set()
                    for i in range(tok_idx + 1, len(toks) - 1):
                        x = toks[i]
                        if isinstance(x, list):
                            x = recur(x)
                        else:
                            x = get_unit_obj(x)
                        obj.add(x)
                    return frozenset(obj)

                if tok.token == Token.LBRACKET:
                    obj = []
                    for i in range(tok_idx + 1, len(toks) - 1):
                        x = toks[i]
                        if isinstance(x, list):
                            x = recur(x)
                        else:
                            x = get_unit_obj(x)
                        obj.append(x)
                    return obj

                if tok.token == Token.LPAREN:
                    obj = []
                    for i in range(tok_idx + 1, len(toks) - 1):
                        x = toks[i]
                        if isinstance(x, list):
                            x = recur(x)
                        else:
                            x = get_unit_obj(x)
                        obj.append(x)
                    return tuple(obj)

                return get_unit_obj(tok)

            raise InvalidOptionValue(f'Value cannot be converted to native type: {self.value}')

        stuff = recur(self.toks)
        return stuff

def parse_value(value: str):
    ''' Turn a value string into a value object. '''
    ast = Ast(value)
    return ast.objectify()
