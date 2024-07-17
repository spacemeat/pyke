''' Abstracting an Options owner.'''

from copy import deepcopy
from typing import Type, TypeVar, Iterable, Any

from .options import Options
from .utilities import determine_color_support, ansi_colors

T = TypeVar('T')

class OptionsOwner:
    ''' Base class for classes that own an Options object. '''
    def __init__(self):
        color_table_ansi_24bit = deepcopy(ansi_colors['colors_24bit'])
        color_table_ansi_8bit = deepcopy(ansi_colors['colors_8bit'])
        color_table_ansi_named = deepcopy(ansi_colors['colors_named'])
        color_table_none = deepcopy(ansi_colors['colors_none'])
        supported_terminal_colors = determine_color_support()

        self.options = Options()
        self.options |= {
            # Interpolated value for None.
            'none': None,
            # Interpolated value for True.
            'true': True,
            # Interpolated value for False.
            'false': False,
            # The verbosity of reporting. 0 just reports the phase by name; 1 reports the phase's
            # interpolated options; 2 reports the raw and interpolated options.
            'report_verbosity': 2,
            # Whether to print full paths, or relative to $CWD when reporting.
            'report_relative_paths': True,
            # The verbosity of non-reporting actions. 0 is silent, unless there are errors; 1 is an
            # abbreviated report; 2 is a full report with all commands run.
            'verbosity': 0,
            # 24-bit ANSI color table.
            'colors_24bit': color_table_ansi_24bit,
            # 8-bit ANSI color table.
            'colors_8bit': color_table_ansi_8bit,
            # Named ANSI color table.
            'colors_named': color_table_ansi_named,
            # Color table for no ANSI color codes.
            'colors_none': color_table_none,
            # Color table accessor based on {colors}.
            'colors_dict': '{colors_{colors}}',
            # Color table selector. 24bit|8bit|named|none
            'colors': supported_terminal_colors,
        }

    @property
    def name(self):
        ''' Quick property to get the name option.'''
        return self.opt_str('name')

    @name.setter
    def name(self, value):
        ''' Quick property to set the name options.'''
        self.push_opts({'name': value})

    @property
    def group(self):
        ''' Quick property to get the group name.'''
        return self.opt_str('group')

    @property
    def full_name(self):
        """The def full_name property."""
        group = self.opt_str('group')
        return f"{self.opt_str('group')}.{self.name}" if len(group) > 0 else self.name

    def push_opts(self, overrides: dict):
        ''' Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line. '''
        self.options |= overrides

    def pop_opts(self, keys: list[str]):
        ''' Removes pushed option overrides. '''
        for key in keys:
            self.options.pop(key)

    def opt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace. '''
        if overrides:
            self.options |= overrides
        val = self.options.get(key, interpolate)
        if overrides:
            for k in overrides.keys():
                self.options.pop(k)
        return val

    def opt_t(self, obj_type: Type[T], key: str, overrides: dict | None = None,
              interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a T. '''
        val = self.opt(key, overrides, interpolate)
        if interpolate:
            if not isinstance(val, obj_type):
                raise TypeError(f'{self.full_name}:{key} does not match exptected type {obj_type}.'
                                f' Seems to be a {type(val)} instead.')
        return val

    def opt_iter(self, key: str, overrides: dict | None = None,
                 interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a tuple. '''
        return self.opt_t(Iterable, key, overrides, interpolate)

    def opt_bool(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a bool. '''
        return self.opt_t(bool, key, overrides, interpolate)

    def opt_int(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be an int. '''
        return self.opt_t(int, key, overrides, interpolate)

    def opt_float(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a float. '''
        return self.opt_t(float, key, overrides, interpolate)

    def opt_str(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a string. '''
        return self.opt_t(str, key, overrides, interpolate)

    def opt_tuple(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a tuple. '''
        return self.opt_t(tuple, key, overrides, interpolate)

    def opt_list(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a list. '''
        return self.opt_t(list, key, overrides, interpolate)

    def opt_set(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a set. '''
        return self.opt_t(set, key, overrides, interpolate)

    def opt_dict(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> Any:
        ''' Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a dict. '''
        return self.opt_t(dict, key, overrides, interpolate)

