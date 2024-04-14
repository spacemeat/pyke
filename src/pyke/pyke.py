'''
Python library for building software.
'''

# pylint: disable=broad-exception-caught

# TODO: Lots of good goals outlined here:  https://www.youtube.com/watch?v=Sh3uayB9kHs

from enum import Enum
import importlib.util
import importlib.machinery
import os
from pathlib import Path
import sys
import json
import traceback

from .action import Action
from .options import OptionOp
from .options_parser import parse_value
from .phases.phase import Phase
from .phases.project import ProjectPhase
from .utilities import WorkingSet, MalformedConfigError, ensure_list

def main_project():
    ''' Returns the main project created for the makefile.'''
    return WorkingSet.main_phase

class ReturnCode(Enum):
    ''' Encoded return code for program exit.'''
    SUCCEEDED = 0
    MAKEFILE_NOT_FOUND = 1
    MAKEFILE_DID_NOT_LOAD = 2
    INVALID_ARGS = 3
    ACTION_FAILED = 4

def run_make_file(pyke_path, cache_make):
    ''' Loads and runs the user-created make file.'''
    if pyke_path.exists():
        try:
            sys.dont_write_bytecode = not cache_make
            spec = importlib.util.spec_from_file_location('pyke', pyke_path)
            if spec:
                module = importlib.util.module_from_spec(spec)
                loader = spec.loader
                if loader:
                    loader.exec_module(module)
                    sys.dont_write_bytecode = cache_make
                    return
        except Exception:
            print (f'"{pyke_path}" could not be loaded.')
            traceback.print_exc()
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

Looks for ./make.py && loads the project phase && runs the default action.
$ pyke
$ pyke -m .

Looks for ./simple_test.py && loads the project phase && runs the default action.
$ pyke -m ./simple_test.py

Looks for ../../make.py && loads the project phase && runs the default
action from the current directory. This will emplace build targets relative to ../../.
$ pyke -m ../../

Looks for ../../make.py && loads the project phase && runs the default
action from the current directory. This will emplace build targets relative to ./.
$ pyke -m../../ -o anchor:$PWD

Looks for ./make.py && loads && runs the default action, overriding the options in the loaded
phase and all dependent phases.
$ pyke -o kind:debug -o verbosity:0

Looks for ./make.py && loads the phase named "alt_project" && runs its default action.
$ pyke -p alt_project

Looks for ./make.py && loads the project phase && runs the action named "build"
$ pyke build

Looks for ./make.py && loads && overrides the "time_run" option && runs the "clean", "build", 
and "run" actions successively, given the success of each previous action.
$ pyke -o time_run:true clean build run

Looks for ./make.py && loads && runs the "clean" and "build" actions && then overrides the
"time_run" option and runs the "run" action.
$ pyke clean build -otime_run:true run
    ''')

def load_config():
    ''' Loads aliases from ~/.config/pyke/pyke-config.json or <project-root>/pyke-config.json or
        <cwd>/pyke-config.json, overriding in that order. '''
    def process_config(config):
        if not isinstance(config, dict):
            raise MalformedConfigError(f'Config file {file}: Must be a JSON dictonary.')

        def read_block(config, subblock, keyname) -> dict[str, list[str]]:
            rets = {}
            if aliases := config.get(subblock):
                if not isinstance(aliases, dict):
                    raise MalformedConfigError(
                        f'Config file {file}: "{subblock}" must be a dictionary.')
                for alias, values in aliases.items():
                    if not isinstance(alias, str):
                        raise MalformedConfigError(
                            f'Config file {file}: "{config}/{keyname}" key must be a string.')
                    if isinstance(values, str):
                        values = [values]
                    if (not isinstance(values, list) or
                        any(not isinstance(value, str) for value in values)):
                        raise MalformedConfigError(
                            f'Config file {file}: "{config}/{keyname}" value must be a string '
                            'or a list of strings.')
                    rets[alias] = values
            return rets

        WorkingSet.argument_aliases |= read_block(config, 'argument_aliases', 'argument')
        WorkingSet.action_aliases |= read_block(config, 'action_aliases', 'action')

    def set_default_config():
        default_config = '''
{
    "argument_aliases": {
        "-v0": "-overbosity=0",
        "-v1": "-overbosity=1",
        "-v2": "-overbosity=2",
        "-release": "-okind=release",
        "-versioned_sos": ["-oposix_shared_object_file={posix_so_real_name}",
                           "-ogenerate_versioned_sonames=True"],
        "vsos": ["-oposix_shared_object_file={posix_so_real_name}",
                 "-ogenerate_versioned_sonames=True"],

        "-deploy_install": ["-orpath_deps=False",
                            "-omoveable_binaries=False",
                            "-oposix_shared_object_file={posix_so_real_name}",
                            "-ogenerate_versioned_sonames=true",
                            "-okind=release"],
        "-deploy_moveable": ["-orpath_deps=True",
                             "-omoveable_binaries=True",
                             "-oposix_shared_object_file={posix_so_linker_name}",
                             "-ogenerate_versioned_sonames=false",
                             "-okind=release"]
    },
    "action_aliases": {
        "opts": "report_options",
        "files": "report_files",
        "c": "clean",
        "cbd": "clean_build_directory",
        "b": "build"
    }
} '''
        config = json.loads(default_config)
        process_config(config)

    set_default_config()

    for direc in list(dict.fromkeys([
            Path.home() / '.config' / 'pyke',
            WorkingSet.makefile_dir,
            Path.cwd()])):
        file = Path(direc) / 'pyke-config.json'
        try:
            with open(file, 'r', encoding='utf-8') as fi:
                config = json.load(fi)
                process_config(config)
        except (FileNotFoundError, MalformedConfigError):
            pass

def uniquify_phase_names():
    ''' Ensure phase names are unique within groups.'''
    names = {}
    for phase in WorkingSet.main_phase.enumerate_dependencies():
        fullname = phase.full_name
        if fullname in names:
            c, lp = names[fullname]
            lp.append(phase)
            names[fullname] = (c + 1, lp)
        else:
            names[fullname] = (1, [phase])
    for _, (count, phases) in names.items():
        if count > 1:
            idx = 0
            for phase in phases:
                new_name = phase.name
                new_full_name = new_name
                if len(phase.group) > 0:
                    new_full_name = f'{phase.group}.{new_name}'
                while new_full_name in names:
                    new_name = f'{phase.name}_{idx}'
                    new_full_name = f'{phase.group}.{new_name}'
                    idx += 1
                phase.name = new_name

def get_phases(labels: list[str] | str) -> list[Phase]:
    ''' Returns all phases that match the labels filter.
    labels is a list of strings. For each label, some phases may be returned:
    'foo' specifies a phase with no group set, whose name is 'foo'
    '@' specifies all phases with no group set, with any name
    '.foo' specifies a phase with no group set, whose name is 'foo'
    '.@' specifies all phases with no group set, with any name
    '@.foo' specifies all phases in any group (or none), whose name is 'foo'
    'bar.@' specifies all phases in group 'bar'
    'bar.foo' specifies a phase in group 'bar' named 'foo'
    '@.@' specifies all phases
    '''
    phases = []
    labels = ensure_list(labels)
    for label in labels:
        group_phase_label = label.split('.', 1)
        if len(group_phase_label) == 1:
            label = group_phase_label[0]
            for phase in WorkingSet.main_phase.enumerate_dependencies():
                if label in ['@', phase.full_name]:
                    phases.append(phase)
        elif len(group_phase_label) == 2:
            grouplabel, namelabel = group_phase_label
            for phase in WorkingSet.main_phase.enumerate_dependencies():
                if grouplabel in ['@', phase.group]:
                    if namelabel in ['@', phase.name]:
                        phases.append(phase)
    return list(reversed(phases))

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

    load_config()

    project_phase_name = 'project_' + (make_path.parent.name if
        make_path.name == 'make.py'
        else make_path.stem)
    WorkingSet.main_phase = ProjectPhase({
        'name': project_phase_name})

    run_make_file(make_path, cache_make)
    uniquify_phase_names()

    actions = []
    file_operations_are_dirty = True

    args = []
    for arg in sys.argv[idx:]:
        args.extend(WorkingSet.argument_aliases.get(arg, [arg]))

    idx = 0
    while idx < len(args):
        arg = args[idx]

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

        if arg.startswith('-o') or arg == '--override':
            override = ''
            if len(arg) > 2:
                override = arg[2:]
            else:
                idx += 1
                override = args[idx]

            affected_phases = []
            if ':' in override:
                phase_labels, override = override.split(':', 1)
                affected_phases = get_phases(phase_labels)
            else:
                affected_phases = get_phases('@.@')

            if '=' in override:
                k, v = override.split('=', 1)
                if k[-1] in ['+', '*', '-', '|', '&', '\\', '^']:
                    #op_str = f'{k[-1]}='
                    op = {member.value: member for member in OptionOp}[k[-1]]
                    #k = k[:-1].strip()
                else:
                    op = OptionOp.REPLACE
                v = parse_value(v.strip())
                for active_phase in affected_phases:
                    active_phase.push_opts({k: (op, v)})
            else:
                for active_phase in affected_phases:
                    active_phase.pop_opts([override])

            file_operations_are_dirty = True

        else:
            if file_operations_are_dirty:
                WorkingSet.main_phase.patch_options_in_dependencies()
                WorkingSet.main_phase.compute_file_operations_in_dependencies()
                file_operations_are_dirty = False

            affected_phases = []
            if ':' in arg:
                phase_labels, arg = arg.split(':', 1)
                affected_phases = get_phases(phase_labels)
            else:
                affected_phases = get_phases('@.@')

            arg = WorkingSet.action_aliases.get(arg, [arg])[0]
            action = Action(arg)
            actions.append(action)
            for active_phase in affected_phases:
                active_phase.do(action)

        idx += 1

    for action in actions:

        res = action.run()
        if res.failed():
            return ReturnCode.ACTION_FAILED.value

    return ReturnCode.SUCCEEDED.value

if __name__ == '__main__':
    main()
