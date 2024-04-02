''' Utility bits for various modules.'''

import re
from pathlib import Path
import subprocess

from . import ansi as a

class PykeException(Exception):
    ''' Parent for all Pyke errors. '''

class ProjectNameCollisionError(PykeException):
    ''' Raised when more than one project phase shares a name in a hierarchy. '''

class MalformedConfigError(PykeException):
    ''' Raised when reading an incorrectly formatted config file. '''

class PhaseNotFoundError(PykeException):
    ''' Raised when referencing a phase by name which does not match any existing phase. '''

class ProjectPhaseDependencyError(PykeException):
    ''' Raised when a non-project Phase is set to depend on a project Phase. Only projects may
    depend on projects. '''

class InvalidActionError(PykeException):
    ''' Raised when invalid operations on actions are attempted. '''

class InvalidOptionOverrideError(PykeException):
    ''' Raised when referencing an option which was not given a default. '''

class UnsupportedToolkitError(PykeException):
    ''' Raised when a toolkit is specified that is not supported. '''

class UnsupportedLanguageError(PykeException):
    ''' Raised when a language is specified that is not supported. '''

class CircularDependencyError(PykeException):
    ''' Raised when a circular phase dependency is attempted. '''

class InvalidOptionValue(PykeException):
    ''' Raised when attempting to set a value to an option with an incompatible type. '''

class InvalidOptionKey(PykeException):
    ''' Raised when an option is referenced which is not allowed for this phase. '''

class InvalidOptionOperation(PykeException):
    ''' Raised when an option operation is not type-compatible. '''

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
    ''' Places an object in a list if it isn't already. '''
    return o if isinstance(o, list) else [o]

def ensure_tuple(o):
    ''' Places an object in a tuple if it isn't already. '''
    return o if isinstance(o, tuple) else (o,)

def input_path_is_newer(in_path: Path, out_path: Path):
    ''' Compares the modified times of two files.
    in_path: Path to an input file. This file must exist.
    out_path: Path to an output file. If this file does not exist, it is considered older than the
    input file. '''
    if not in_path.exists():
        raise ValueError(f'Input file "{in_path}" does not exist; cannot compare m-times.')

    outm = out_path.stat().st_mtime if out_path.exists() else 0
    inm = in_path.stat().st_mtime
    return inm > outm

def do_shell_command(cmd):
    ''' Reports, and then performs the given shell command as a subprocess. It is run in its
    own shell instance, each with its own environment. '''
    res = subprocess.run(cmd, shell=True, capture_output=True, encoding='utf-8', check = False)
    return (res.returncode, res.stdout, res.stderr)

class WorkingSet:
    ''' Keeps track of globally-available values.'''
    makefile_dir = ''
    action_aliases = {}
    main_phase = None
    phase_map = {}
    report_verbosity = 2
    verbosity = 0
