''' Utility bits for various modules.'''

from __future__ import annotations
import functools
import re
import os
from pathlib import Path
import pty
import subprocess
import typing

from . import ansi as a

if typing.TYPE_CHECKING:
    from .phases.phase import Phase

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

def uniquify_list(o):
    ''' Returns a list of unique items. '''
    return list(dict.fromkeys(o).keys())

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

def any_input_paths_are_newer(in_paths: list[Path], out_paths: list[Path]):
    if any(not in_path.exists() for in_path in in_paths):
        raise ValueError('Input files do not exist; cannot compare m-times.')

    if len(in_paths) == 0 or len(out_paths) == 0:
        return True

    outm = functools.reduce(min,
               [out_path.stat().st_mtime if out_path.exists() else 0 for out_path in out_paths],
               32536799999)
    inm = functools.reduce(max,
                 [in_path.stat().st_mtime for in_path in in_paths], 0)
    return inm > outm

def do_shell_command(cmd):
    ''' Reports, and then performs the given shell command as a subprocess. It is run in its
    own shell instance, each with its own environment. '''
    res = subprocess.run(cmd, shell=True, capture_output=True, encoding='utf-8', check = False)
    return (res.returncode, res.stdout, res.stderr)

def do_interactive_command(cmd):
    ''' Run an interactive command using the CLI that launched pyke.'''
    return os.waitstatus_to_exitcode(pty.spawn(cmd))

# https://gist.github.com/kurahaupo/6ce0eaefe5e730841f03cb82b061daa2
def determine_color_support() -> str:
    ''' Returns whether we can support 24-bit color on this terminal.'''
    if 'COLORTERM' in os.environ and os.environ['COLORTERM'] in ['truecolor', '24bit']:
        return '24bit'

    cmd = 'tput colors'
    ret, out, _ = do_shell_command(cmd)
    if ret == 0 and out == '256':
        return '8bit'

    if ret == 0 and out == '16':
        return 'named'

    return 'none'

class WorkingSet:
    ''' Keeps track of globally-available values.'''
    makefile_dir = ''
    argument_aliases = {}
    action_aliases = {}
    default_action = ''
    default_arguments = []
    main_phase: Phase
    all_phases: set[Phase] = set()

ansi_colors = {
    'colors_24bit': {
        'off':              {'form': 'off' },
        'success':          {'form': 'b24', 'fg': (0x33, 0xaf, 0x55) },
        'fail':             {'form': 'b24', 'fg': (0xff, 0x33, 0x33) },
        'phase_lt':         {'form': 'b24', 'fg': (0x33, 0x33, 0xff) },
        'phase_dk':         {'form': 'b24', 'fg': (0x23, 0x23, 0x7f) },
        'step_lt':          {'form': 'b24', 'fg': (0xb3, 0x8f, 0x4f) },
        'step_dk':          {'form': 'b24', 'fg': (0x93, 0x5f, 0x2f) },
        'shell_cmd':        {'form': 'b24', 'fg': (0x31, 0x31, 0x32) },
        'key':              {'form': 'b24', 'fg': (0x9f, 0x9f, 0x9f) },
        'val_uninterp_lt':  {'form': 'b24', 'fg': (0xaf, 0x23, 0xaf) },
        'val_uninterp_dk':  {'form': 'b24', 'fg': (0x5f, 0x13, 0x5f) },
        'val_interp':       {'form': 'b24', 'fg': (0x33, 0x33, 0xff) },
        'token_type':       {'form': 'b24', 'fg': (0x33, 0xff, 0xff) },
        'token_value':      {'form': 'b24', 'fg': (0xff, 0x33, 0xff) },
        'token_depth':      {'form': 'b24', 'fg': (0x33, 0xff, 0x33) },
        'path_lt':          {'form': 'b24', 'fg': (0x33, 0xaf, 0xaf) },
        'path_dk':          {'form': 'b24', 'fg': (0x13, 0x5f, 0x8f) },
        'file_type_lt':     {'form': 'b24', 'fg': (0x63, 0x8f, 0xcf) },
        'file_type_dk':     {'form': 'b24', 'fg': (0x43, 0x5f, 0x9f) },
        'action_lt':        {'form': 'b24', 'fg': (0xf3, 0x7f, 0x0f) },
        'action_dk':        {'form': 'b24', 'fg': (0xa3, 0x4f, 0x00) },
    },
    'colors_8bit': {
        'off':              {'form': 'off' },
        'success':          {'form': 'b8', 'fg': 77 },
        'fail':             {'form': 'b8', 'fg': 160 },
        'phase_lt':         {'form': 'b8', 'fg': 27 },
        'phase_dk':         {'form': 'b8', 'fg': 19 },
        'step_lt':          {'form': 'b8', 'fg': 215 },
        'step_dk':          {'form': 'b8', 'fg': 137 },
        'shell_cmd':        {'form': 'b8', 'fg': 237 },
        'key':              {'form': 'b8', 'fg': 8 },
        'val_uninterp_lt':  {'form': 'b8', 'fg': 201 },
        'val_uninterp_dk':  {'form': 'b8', 'fg': 90 },
        'val_interp':       {'form': 'b8', 'fg': 27 },
        'token_type':       {'form': 'b8', 'fg': 87 },
        'token_value':      {'form': 'b8', 'fg': 207 },
        'token_depth':      {'form': 'b8', 'fg': 83 },
        'path_lt':          {'form': 'b8', 'fg': 45 },
        'path_dk':          {'form': 'b8', 'fg': 24 },
        'file_type_lt':     {'form': 'b8', 'fg': 111 },
        'file_type_dk':     {'form': 'b8', 'fg': 26 },
        'action_lt':        {'form': 'b8', 'fg': 172 },
        'action_dk':        {'form': 'b8', 'fg': 130 },
    },
    'colors_named': {
        'off':              {'form': 'off' },
        'success':          {'form': 'named', 'fg': 'bright green' },
        'fail':             {'form': 'named', 'fg': 'bright red' },
        'phase_lt':         {'form': 'named', 'fg': 'bright blue' },
        'phase_dk':         {'form': 'named', 'fg': 'blue' },
        'step_lt':          {'form': 'named', 'fg': 'bright yellow' },
        'step_dk':          {'form': 'named', 'fg': 'yellow' },
        'shell_cmd':        {'form': 'named', 'fg': 'bright black' },
        'key':              {'form': 'named', 'fg': 'white' },
        'val_uninterp_lt':  {'form': 'named', 'fg': 'bright magenta' },
        'val_uninterp_dk':  {'form': 'named', 'fg': 'magenta' },
        'val_interp':       {'form': 'named', 'fg': 'bright blue' },
        'token_type':       {'form': 'named', 'fg': 'bright cyan' },
        'token_value':      {'form': 'named', 'fg': 'bright magenta' },
        'token_depth':      {'form': 'named', 'fg': 'bright green' },
        'path_lt':          {'form': 'named', 'fg': 'bright cyan' },
        'path_dk':          {'form': 'named', 'fg': 'cyan' },
        'file_type_lt':     {'form': 'named', 'fg': 'bright blue' },
        'file_type_dk':     {'form': 'named', 'fg': 'blue' },
        'action_lt':        {'form': 'named', 'fg': 'bright yellow' },
        'action_dk':        {'form': 'named', 'fg': 'yellow' },
    },
    'colors_none': {
        'off':              {},
        'success':          {},
        'fail':             {},
        'phase_lt':         {},
        'phase_dk':         {},
        'step_lt':          {},
        'step_dk':          {},
        'shell_cmd':        {},
        'key':              {},
        'val_uninterp_lt':  {},
        'val_uninterp_dk':  {},
        'val_interp':       {},
        'token_type':       {},
        'token_value':      {},
        'token_depth':      {},
        'path_lt':          {},
        'path_dk':          {},
        'file_type_lt':     {},
        'file_type_dk':     {},
        'action_lt':        {},
        'action_dk':        {},
    },
}

def set_color(color_set: dict[str, dict[str, str]], color: str):
    ''' Returns the ANSI color code for the specified thematic element.'''
    color_desc = color_set[color]
    if color_desc is not None:
        fg = color_desc.get('fg')
        bg = color_desc.get('bg')
        form = color_desc.get('form')
        if form == 'off':
            return a.off
        if form == 'b24':
            assert fg is None or isinstance(fg, tuple)
            assert bg is None or isinstance(bg, tuple)
            return (f'{a.b24_fg(fg) if fg else ""}'
                    f'{a.b24_bg(bg) if bg else ""}')
        if form == 'b8':
            assert fg is None or isinstance(fg, int)
            assert bg is None or isinstance(bg, int)
            return (f'{a.b8_fg(fg) if fg else ""}'
                    f'{a.b8_bg(bg) if bg else ""}')
        if form == 'named':
            assert fg is None or isinstance(fg, str)
            assert fg is None or isinstance(bg, str)
            return (f'{a.named_fg[fg] if fg else ""}'
                    f'{a.named_bg[bg] if bg else ""}')
    return ''
