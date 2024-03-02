''' Utility bits for various modules.'''

import re

class InvalidOptionValue(Exception):
    '''
    Raised when attempting to set a value to an option with an incompatible type.
    '''

class InvalidOptionKey(Exception):
    '''
    Raised when an option is referenced which is not allowed for this phase.
    '''

class InvalidOptionOperation(Exception):
    '''
    Raised when an option operation is not type-compatible.
    '''


re_interp_option = re.compile(r'{([a-zA-Z0-9_]+?)}')

def is_str_int(s):
    ''' Is the object an int? '''
    try:
        v = int(s)
        return isinstance(v, int)
    except ValueError:
        return False

def is_str_float(s):
    ''' Is the object a float? '''
    try:
        v = float(s)
        return isinstance(v, float)
    except ValueError:
        return False
