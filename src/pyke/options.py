''' Options class and friends.'''
# pylint: disable=too-many-boolean-expressions, too-many-branches, too-few-public-methods
# pylint: disable=consider-using-generator
import copy
from enum import Enum
from typing import Any
from .options_parser import parse_value
from .utilities import (re_interp_option, InvalidOptionOperation)


class OptionOp(Enum):
    ''' The operations you can perform with option overrides.'''
    REPLACE = '='
    NOT = '!='       # not booleans
    ADD = '+='       # add numbers, add to strings
    SUBTRACT = '-='  # subtract numbers, remove matching substrings
    MULTIPLY = '*='  # multiply numbers
    DIVIDE = '/='    # divide numbers
    APPEND = '+='    # append to lists/tuples, add to sets, union to dicts
    REMOVE = '-='    # remove by value from lists and sets and tuples
    EXTEND = '*='    # extend to lists/tuples
    UNION = '|='     # union of sets and dicts
    INTERSECT = '&=' # intersection of sets
    DIFF = '\\='     # remove by index from lists/tuples, by key from dict, difference of sets
    SYM_DIFF = '^='  # sym_diff of sets

    @staticmethod
    def get(op: str):
        ''' Return the OptionOp by string.'''
        op_val = {member.value: member for member in OptionOp}.get(op)
        if not op_val:
            raise InvalidOptionOperation(f'Invalid option override "{op}"')
        return op_val

class Op:
    ''' Represents an option override and its operator.'''
    def __init__(self, operator: str | OptionOp, value: Any):
        self.operator: OptionOp = (operator if isinstance(operator, OptionOp)
                                   else OptionOp.get(operator))
        self.value: str = value

class Option:
    ''' Represents a named option. Stores all its overrides.'''
    def __init__(self, name: str, value):
        self.name = name
        self.value_stack: list[Op] = []
        self.value_stack.append(Op(OptionOp.REPLACE, value))

    def push(self, op: Op):
        ''' Sets a value to this Option, as an override to previous values. '''
        self.value_stack.append(op)

    def pop(self):
        ''' Removes the last override.'''
        del self.value_stack[-1]

# TODO: Track and flag circular refs.
class Options:
    ''' Holds the collection of options for a particular phase. '''
    def __init__(self):
        self.opts: dict[str, Option] = {}

    def __ior__(self, new_opts: dict[str, Op | Any]):
        for k, v in new_opts.items():
            self.push(k, v)
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

    def push(self, key: str, value: Op | Any):
        ''' Push an option override.'''
        if not isinstance(value, Op):
            value = Op(OptionOp.REPLACE, value)

        if key not in self.opts:
            self.opts[key] = Option(key, value.value)
        else:
            self.opts[key].push(value)

    def pop(self, key):
        ''' Pop the latest option override.'''
        self.opts[key].pop()

    def get(self, key, interpolate=True):
        ''' Get the ultimate value of the option.'''
        opt = self.opts.get(key)
        if opt is None:
            return f'!{key}!'
        values = copy.deepcopy(opt.value_stack)
        if not interpolate:
            return values

        def interp(v) -> Any:
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
                # NOTE: linter is telling me to use this; I think I want to use ([x for x in y])
                val = tuple([interp(ve) for ve in val])
                return val

            if isinstance(val, (set, frozenset)):
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

        values = [Op(value.operator, interp(value.value)) for value in values]

        # now merge them according to ops
        computed = values[0].value
        for val in values[1:]:
            computed = self._apply_op(computed, val.value, val.operator)

        return computed

    def _apply_op(self, computed, override, op):
        if op == OptionOp.REPLACE:
            return override

        if isinstance(computed, bool):
            if op == OptionOp.NOT:
                if isinstance(override, bool):
                    return not override
            raise InvalidOptionOperation(
                'Operator on bools must be !.')

        if isinstance(computed, (int, float)):
            if op == OptionOp.ADD:
                if isinstance(override, (int, float)):
                    return computed + override
            if op == OptionOp.SUBTRACT:
                if isinstance(override, (int, float)):
                    return computed - override
            if op == OptionOp.MULTIPLY:
                if isinstance(override, (int, float)):
                    return computed * override
            if op == OptionOp.DIVIDE:
                if isinstance(override, (int, float)) and float(override) != 0.0:
                    return computed / override
            raise InvalidOptionOperation(
                'Operators on ints or floats must be +, -, *, /, and not dividing by 0.')

        if isinstance(computed, str):
            if op == OptionOp.ADD:
                return f'{computed}{override}'
            if op == OptionOp.SUBTRACT:
                overstr = str(override)
                if (idx := computed.find(overstr)) >= 0:
                    return computed[:idx] + computed[idx + len(overstr):]
                return computed
            raise InvalidOptionOperation(
                'Operators on string options must be + or -.')

        if isinstance(computed, list):
            if op == OptionOp.APPEND:
                return [*computed, override]
            if op == OptionOp.EXTEND:
                if isinstance(override, (list, tuple)):
                    return [*computed, *override]
                raise InvalidOptionOperation('Lists can be extended only by other lists or tuples.')
            if op == OptionOp.REMOVE:
                return [e for e in computed if e != override]
            if op == OptionOp.DIFF:
                if isinstance(override, int):
                    return [e for i, e in enumerate(computed) if i != override]
                if isinstance(override, (list, tuple, set)):
                    if all(isinstance(e, int) for e in override):
                        return [e for i, e in enumerate(computed) if i not in override]
                raise InvalidOptionOperation('Remove from list operands must be by integer index.')

        if isinstance(computed, tuple):
            if op == OptionOp.APPEND:
                return (*computed, override)
            if op == OptionOp.EXTEND:
                if isinstance(override, (list, tuple)):
                    return (*computed, *override)
                raise InvalidOptionOperation(
                    'Tuples can be extended only by other lists or tuples.')
            if op == OptionOp.REMOVE:
                return tuple([e for e in computed if e != override])
            if op == OptionOp.DIFF:
                if isinstance(override, int):
                    return tuple([e for i, e in enumerate(computed) if i != override])
                if isinstance(override, (list, tuple, set)):
                    if all(isinstance(e, int) for e in override):
                        return tuple([e for i, e in enumerate(computed) if i not in override])
                raise InvalidOptionOperation('Remove from tuple operands must be by integer index.')

        if isinstance(computed, (set, frozenset)):
            if op == OptionOp.APPEND:
                return {*computed, override}
            if op == OptionOp.REMOVE:
                return computed - {override}
            if op == OptionOp.UNION:
                if isinstance(override, (set, frozenset)):
                    return computed | override
                raise InvalidOptionOperation('Union operands must be sets.')
            if op == OptionOp.INTERSECT:
                if isinstance(override, (set, frozenset)):
                    return computed & override
                raise InvalidOptionOperation('Intersect operands must be sets.')
            if op == OptionOp.DIFF:
                if isinstance(override, (set, frozenset)):
                    return computed - override
                raise InvalidOptionOperation('Difference operands must be sets.')
            if op == OptionOp.SYM_DIFF:
                if isinstance(override, (set, frozenset)):
                    return computed ^ override
                raise InvalidOptionOperation('Symmetric difference operands must be sets.')

        if isinstance(computed, dict):
            if op in [OptionOp.APPEND, OptionOp.UNION]:
                if not isinstance(override, dict):
                    raise InvalidOptionOperation('Append/union operands to dicts must be dicts.')
                return computed | override
            if op == OptionOp.REMOVE:
                if isinstance(override, (list, tuple, set, frozenset)):
                    return {k: v for k, v, in computed.items() if k not in override}
                return {k: v for k, v in computed.items() if k != override}

        raise InvalidOptionOperation('Invalid operation for this option.')
