'''
Python library for building software.
'''

from enum import Enum
import importlib.util
import importlib.machinery
import os
from pathlib import Path
import sys

from .options_parser import parse_value
from .phases.phase import Phase
from .utilities import WorkingSet


class ReturnCode(Enum):
    ''' Encoded return code for program exit.'''
    SUCCEEDED = 0
    MAKEFILE_NOT_FOUND = 1
    MAKEFILE_DID_NOT_LOAD = 2
    INVALID_ARGS = 3
    ACTION_FAILED = 4


def use_phases(phases: Phase | list[Phase] | tuple[Phase]):
    '''
    Called by the user's pyke program to register phases for use in the project.
    '''
    if isinstance(phases, Phase):
        phases = [phases]
    else:
        phases = list(phases)
    WorkingSet.using_phases.extend(phases)


def run_make_file(pyke_path, cache_make):
    ''' Loads and runs the user-created make file.'''
    if pyke_path.exists:
        sys.dont_write_bytecode = not cache_make
        spec = importlib.util.spec_from_file_location('pyke', pyke_path)
        if spec:
            module = importlib.util.module_from_spec(spec)
            loader = spec.loader
            if loader:
                loader.exec_module(module)
                sys.dont_write_bytecode = cache_make
                return
        print (f'"{pyke_path}" could not be loaded.')
        sys.exit(ReturnCode.MAKEFILE_DID_NOT_LOAD.value)
    else:
        print (f'"{pyke_path}" was not found.')
        sys.exit(ReturnCode.MAKEFILE_NOT_FOUND.value)


def print_version():
    ''' Print the version.'''
    # TODO: autoomate this against git tag
    print ('pyke version 0.0.1')


def print_help():
    ''' Send help.'''
    print (
    '''
Runs an action on a phase's dependencies, followed by the phase itself. The phase,
action, and any overrides are extracted from args. The following arguments are available:
-v, --version: Prints the version information for pyke, and exits.
-h, --help: Prints a help document.
-c, --cache_makefile: Allows the makefile's __cache__ to be generated. This might speed up
    complex builds, but they'd hvae to be really complex. Must precede any arguments that 
    are not -v, -h, or -m.
-m, --module: Specifies the module (pyke file) to be run. Must precede any arguments that
    are not -v, -h, or -c. Actions are performed relative to the module's directory, unless an
    option override (-o anchor:[dir]) is given, in which case they are performed relative to
    the given working directory. Immediately after running the module, the active phase
    is selected as the last phase added to use_phase()/use_phases(). This can be overridden
    by -p.
    If no -m argument is given, pyke will look for and run ./make.py.
-o, --override: Specifies an option override in all phases for subsequenet actions. If the
    option is given as a key:value pair, the override is set; if it is only a key (with no
    separator ':') the override is clear. Option overrides are kept as a stack; if you set
    an override n times, you must clear it n times to restore the original value. Note,
    you can set and clear individual overrides out of order:
    $ pyke -o kind:debug -o kind:release -o exe_basename:whodunnit -o kind
    will end up overriding "kind" to "debug" and "exe_basename" to "whodunnit", like one
    might hope.
-p, --phase: Specifies the active phase to use for subsequent option overrides and actions.
action: Arguments given without switches specify actions to be taken on the active phase's
    dependencies, and then the active phase itself, in depth-first order. Any action on any
    phase which doesn't support it is quietly ignored.

Returns the version number.
$ pyke -v

Looks for ./make.py && loads the last phase in _using_phases && runs the default action.
$ pyke
$ pyke -m .

Looks for ./simple_test.py && loads the last phase in _using_phases && runs the default action.
$ pyke -m ./simple_test.py

Looks for ../../make.py && loads the last phase in _using_phases && runs the default
action from the current directory. This will emplace build targets relative to ../../.
$ pyke -m ../../

Looks for ../../make.py && loads the last phase in _using_phases && runs the default
action from the current directory. This will emplace build targets relative to ./.
$ pyke -m../../ -o anchor:$PWD

Looks for ./make.py && loads && runs the default action, overriding the options in the loaded
phase and all dependent phases.
$ pyke -o kind:debug -o verbosity:0

Looks for ./make.py && loads the phase named "alt_project" && runs its default action.
$ pyke -p alt_project

Looks for ./make.py && loads the last phase && runs the action named "build"
$ pyke build

Looks for ./make.py && loads && overrides the "time_run" option && runs the "clean", "build", 
and "run" actions successively, given the success of each previous action.
$ pyke -o time_run:true clean build run

Looks for ./make.py && loads && runs the "clean" and "build" actions && then overrides the
"time_run" option and runs the "run" action.
$ pyke clean build -otime_run:true run
    ''')

def main():
    '''Entrypoint for pyke.'''
    current_dir = os.getcwd()
    make_file = 'make.py'
    cache_make = False

    idx = 1
    while idx < len(sys.argv):
        arg = sys.argv[idx]

        if arg in ['-v', '--version']:
            print_version()
            return ReturnCode.SUCCEEDED.value

        if arg in ['-h', '--help']:
            print_help()
            return ReturnCode.SUCCEEDED.value

        if arg in ['-c', '--cache_makefile']:
            cache_make = True
            idx += 1
            continue

        if arg.startswith('-m') or arg == '--module':
            make_file = ''
            if len(arg) > 2:
                make_file = sys.argv[idx][2:]
            else:
                idx += 1
                make_file = sys.argv[idx]
            idx += 1
            continue

        break

    make_path = Path(current_dir) / make_file
    if not make_file.endswith('.py'):
        make_path = make_path / 'make.py'

    WorkingSet.makefile_dir = str(make_path.parent)
    run_make_file(make_path, cache_make)

    active_phase = WorkingSet.using_phases[-1]
    phase_map = {phase.opt_str('name'): phase for phase in WorkingSet.using_phases}

    while idx < len(sys.argv):
        arg = sys.argv[idx]

        if arg in ['-v', '--version']:
            print_version()
            return ReturnCode.SUCCEEDED.value

        if arg in ['-h', '--help']:
            print_help()
            return ReturnCode.SUCCEEDED.value

        if arg in ['-c', '--cache_makefile', '--module'] or arg.startswith('-m'):
            print (f'{arg} must precede any of -p (--phase), -o (--override), '
                   'or any action arguments.')
            return ReturnCode.INVALID_ARGS.value

        if arg.startswith('-p') or arg == '--phase':
            phase_name = ''
            if len(arg) > 2:
                phase_name = arg[2:]
            else:
                idx += 1
                phase_name = sys.argv[idx]
            active_phase = phase_map[phase_name]

        elif arg.startswith('-o') or arg == '--override':
            override = ''
            if len(arg) > 2:
                override = arg[2:]
            else:
                idx += 1
                override = sys.argv[idx]
            if ':' in override:
                k, v = override.split(':', 1)
                v = parse_value(v)
                active_phase.push_opts({k: v})
            else:
                active_phase.pop_opts([override])

        else:
            action = arg
            if not active_phase.do(action):
                return ReturnCode.ACTION_FAILED.value

        idx += 1

    return ReturnCode.SUCCEEDED.value

if __name__ == '__main__':
    main()
