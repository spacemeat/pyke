''' Options class and friends.'''
# pylint: disable=too-many-boolean-expressions, too-many-branches
import copy
from enum import Enum
from .utilities import (re_interp_option, InvalidOptionOperation)


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
                if isinstance(override, str):
                    return {k: v for k, v in computed.items() if k != override}
                if isinstance(override, (list, tuple, set, frozenset)):
                    if all((isinstance(e, str) for e in override)):
                        return {k: v for k, v, in computed.items() if k not in override}
                raise InvalidOptionOperation(
                    'Remove operands from dicts must be lists, tuples, or sets.')

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
