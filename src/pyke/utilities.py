''' Utility bits for various modules.'''

import re
from pathlib import Path
import subprocess

from . import ansi as a

class PykeException(Exception):
    '''
    Parent for all Pyke errors.
    '''

class PhaseNotFoundError(PykeException):
    '''
    Raised when referencing a phase by name which does not match any existing phase.
    '''

class ProjectPhaseDependencyError(PykeException):
    '''
    Raised when a non-project Phase is set to depend on a project Phase. Only projects may
    depend on projects.
    '''

class InvalidActionError(PykeException):
    '''
    Raised when invalid operations on actions are attempted.
    '''

class InvalidOptionOverrideError(PykeException):
    '''
    Raised when referencing an option which was not given a default.
    '''

class UnsupportedToolkitError(PykeException):
    '''
    Raised when a toolkit is specified that is not supported.
    '''

class UnsupportedLanguageError(PykeException):
    '''
    Raised when a language is specified that is not supported.
    '''

class CircularDependencyError(PykeException):
    '''
    Raised when a circular phase dependency is attempted.
    '''

class InvalidOptionValue(PykeException):
    '''
    Raised when attempting to set a value to an option with an incompatible type.
    '''

class InvalidOptionKey(PykeException):
    '''
    Raised when an option is referenced which is not allowed for this phase.
    '''

class InvalidOptionOperation(PykeException):
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

def ensure_list(o):
    '''
    Places an object in a list if it isn't already.
    '''
    return o if isinstance(o, list) else [o]

def ensure_tuple(o):
    '''
    Places an object in a tuple if it isn't already.
    '''
    return o if isinstance(o, tuple) else (o,)

def input_is_newer(in_path: Path, out_path: Path):
    '''
    Compares the modified times of two files.
    '''
    if not in_path.exists():
        raise ValueError(f'Input file "{in_path}" does not exist; cannot compare m-times.')

    outm = out_path.stat().st_mtime if out_path.exists() else 0
    inm = in_path.stat().st_mtime
    return inm > outm

def do_shell_command(cmd):
    '''
    Reports, and then performs the given shell command as a subprocess. It is run in its
    own shell instance, each with its own environment.
    '''
    res = subprocess.run(cmd, shell=True, capture_output=True, encoding='utf-8', check = False)
    return (res.returncode, res.stdout, res.stderr)

class WorkingSet:
    ''' Keeps track of globally-available values.'''
    makefile_dir = ''
    main_phase = None
    colors = {}
    report_verbosity = 2
    report_relative_paths = True
    verbosity = 0

def set_color(color):
    ''' Returns the ANSI color code for the specified thematic element.'''
    color_desc = WorkingSet.colors.get(color)
    if color_desc is not None:
        if color_desc.get('form') == 'rgb24':
            fg = color_desc.get('fg')
            bg = color_desc.get('bg')
            return (f'{a.rgb_fg(*fg) if fg else ""}'
                    f'{a.rgb_bg(*bg) if bg else ""}')
        if color_desc.get('form') == 'named':
            fg = color_desc.get('fg')
            bg = color_desc.get('bg')
            off = color_desc.get('off')
            if isinstance(off, list):
                return f'{a.off}'
            # TODO: The rest
            return ''

    return ''
