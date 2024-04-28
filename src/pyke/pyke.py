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

from . import __version__
from .action import Action
from .options import OptionOp, Op
from .options_parser import parse_value
from .phases.phase import Phase
from .phases.project import ProjectPhase
from .utilities import WorkingSet, MalformedConfigError, ensure_list

def get_main_phase():
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
    print (f'pyke version {__version__}')


def print_help():
    ''' Send help.'''
    print (
    ''' Pyke - a Python-powered build system

Usage:
pyke [invocations]* [phases | overrides | actions]*

invocations:
-v, --version: Prints the version information for pyke, and exits.
-h, --help: Prints a help document.
-c, --cache_makefile: Allows the makefile's __cache__ to be generated. This
    might speed up complex builds, but they'd hvae to be really complex to
    make a noticeable difference.
-m, --makefile: Specifies the makefile (pyke file) to be run. Actions are
    performed relative to the makefile's directory, unless an option override
    (-o gen_anchor=dir/to/gen) is given, in which case they are performed
    relative to the given anchor directory. If no -m argument is given, pyke
    will look for and run ./make.py.

phases:
-p, --phases: Specifies one or more phases to set as active phases for the
    subsequent overrides and actions, providing they do not specify their own.
    The format is:
    -p phases
    'phases' is a comma-separated list of names of phase objects defined in
    the makefile. Defaults to '@.@', which specifies all phases in the project.
    All phases are given a group name and shrot name. 'phases' specifies a list
    of the phases by dotted notation: <group>.<name>. An '@' is a wildcard that
    signifies all groups or names: 'test.@' names every phase in the 'test'
    group. For phases whose group is the same as the main project, you can omit
    the group name. i.e. for a project named 'flexon', the phase 'flexon.link'
    can be specified by '-p link'.
    The phase group specified by -p remains in effect until the next -p is
    encountered. Overrides and actions that specify their own phases overrule
    the -p for that argument, but do not reset it.

overrides:
-o, --override: Specifies an option override for subsequenet actions. The
    format for an override is:
    -o [phases:]option[op-value]
    'phases' is a comma-separated list of names of phase objects defined in
    the makefile. Defaults to '@.@', which specifies all phases in the project.
    This overrules any -p settings for this override.
    'option' specifies the name of an option to modify. 
    'op-value' specifies an operator and value to apply to the option. The
    override is pushed onto a stack for that option. If 'op-value' is not
    present, the option's override stack is popped.

actions:
    Actions are words given without switches. The format for an action is:
    [phases:]action
    'phases' is a comma-separated list of names of phase objects defined in
    the makefile. Defaults to '@.@', which specifies all phases in the project.
    This overrules any -p settings for this action.
    Actions such as clean, build, run can be taken on any or all phases. They
    are performed, along with any overrides, in command order. Typical usage
    involves cleaning and building the entire project.
    If no actions are specified, a default action is performed. The default
    is, by default, 'report_actions' and can be overridden in pyke-config.json.

aliases:
    Aliases are provided for complex overrides, such as -v2 or -debug. These
    are predefined, and can be extended via pyke-config.json, found in the
    project root or ~/.config/pyke.

Examples:
Returns the version number.
$ pyke -v

Looks for ./make.py && loads the project phase && runs the default action.
$ pyke
$ pyke -m .

Looks for ./simple_test.py && loads the project phase && runs the default
action.
$ pyke -m ./simple_test.py

Looks for ../../make.py && loads the project phase && runs the default
action from the current directory. This will emplace build targets relative to
../../.
$ pyke -m ../..

Looks for ../../make.py && loads the project phase && runs the default
action from the current directory. This will emplace build targets relative to
./.
$ pyke -m../.. -o gen_anchor=$PWD

Looks for ./make.py && loads && runs the default action, overriding the options
for the build kind (release build) and verbosity of output.
$ pyke -o kind=debug -o verbosity=2

Looks for ./make.py && runs the 'build' action on the 'alt_project' phase.
$ pyke alt_project:build

Looks for ./make.py && loads the project phase && runs the action named 'build'
on all phases.
$ pyke build

Looks for ./make.py && loads && overrides the 'colors' option && runs the
'clean', 'build", and 'run' actions successively, given the success of each
previous action.
$ pyke -ocolors={colors_none} clean build run
''')

def load_config():
    ''' Loads aliases from ~/.config/pyke/pyke-config.json or <project-root>/pyke-config.json,
    overriding in that order. '''
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
        if default_action := config.get('default_action'):
            if not isinstance(default_action, str):
                raise MalformedConfigError(
                    f'Config file {file}: "default_action" must be a string.')
            WorkingSet.default_action = default_action
        if default_arguments := config.get('default_arguments'):
            if not isinstance(default_arguments, list):
                raise MalformedConfigError(
                    f' Config file {file}: "default_arguments" must be a list of strings.')
            WorkingSet.default_arguments.extend(default_arguments)

    def set_default_config():
        default_config = '''
{
    "argument_aliases": {
        "-v0": "-overbosity=0",
        "-v1": "-overbosity=1",
        "-v2": "-overbosity=2",
        "-rv0": "-oreport_verbosity=0",
        "-rv1": "-oreport_verbosity=1",
        "-rv2": "-oreport_verbosity=2",
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
        "actions": "report_actions",
        "c": "clean",
        "cbd": "clean_build_directory",
        "b": "build"
    },
    "default_action": "report_actions",
    "default_arguments": []
} '''
        config = json.loads(default_config)
        process_config(config)

    set_default_config()

    for direc in list(dict.fromkeys([
            Path.home() / '.config' / 'pyke',
            WorkingSet.makefile_dir])):
        file = Path(direc) / 'pyke-config.json'
        try:
            with open(file, 'r', encoding='utf-8') as fi:
                config = json.load(fi)
                process_config(config)
        except (FileNotFoundError, MalformedConfigError):
            pass

def propagate_group_names():
    ''' Cascades project names to group names in dependency phases.'''
    WorkingSet.main_phase.propagate_group_names('')

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
    'foo' specifies a phase with main group set, whose name is 'foo'
    '@' specifies all phases with main group set, with any name
    '.foo' specifies a phase with main group set, whose name is 'foo'
    '.@' specifies all phases with main group set, with any name
    '@.foo' specifies all phases in any group (or none), whose name is 'foo'
    'bar.@' specifies all phases in group 'bar'
    'bar.foo' specifies a phase in group 'bar' named 'foo'
    '@.@' specifies all phases
    '''
    phases = []
    labels = ensure_list(labels)
    for label in labels:
        if '.' not in label:
            label = f'{WorkingSet.main_phase.name}.{label}'
        if label.startswith('.'):
            label = f'{WorkingSet.main_phase.name}{label}'
        group_phase_label = label.split('.', 1)
        grouplabel, namelabel = group_phase_label
        for phase in WorkingSet.main_phase.enumerate_dependencies():
            if grouplabel in ['@', phase.group]:
                if namelabel in ['@', phase.name]:
                    phases.append(phase)
    return phases

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

    project_phase_name = (make_path.parent.name if
        make_path.name == 'make.py'
        else make_path.stem)
    WorkingSet.main_phase = ProjectPhase({
        'name': project_phase_name})
    WorkingSet.all_phases.add(WorkingSet.main_phase)

    run_make_file(make_path, cache_make)
    propagate_group_names()
    uniquify_phase_names()
    WorkingSet.main_phase.patch_options_in_dependencies()

    actions_done = []
    file_operations_are_dirty = True

    args = []
    for arg in [*WorkingSet.default_arguments, *sys.argv[idx:]]:
        args.extend(WorkingSet.argument_aliases.get(arg, [arg]))

    affected_phases = get_phases('@.@')

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

        if arg.startswith('-p') or arg == '--phases':
            if len(arg) > 2:
                phases = arg[2:]
            else:
                idx += 1
                phases = args[idx]
            affected_phases = get_phases(phases)

        if arg.startswith('-o') or arg == '--override':
            arg_affected_phases = []

            override = ''
            if len(arg) > 2:
                override = arg[2:]
            else:
                idx += 1
                override = args[idx]

            using_phase_addr = False
            if ':' in override:
                if '=' in override:
                    if override.find(':') < override.find('='):
                        using_phase_addr = True
                else:
                    using_phase_addr = True

            if using_phase_addr:
                phase_labels, override = override.split(':', 1)
                arg_affected_phases = get_phases(phase_labels)
            else:
                arg_affected_phases = affected_phases

            if '=' in override:
                k, v = override.split('=', 1)
                if k[-1] in ['+', '*', '-', '|', '&', '\\', '^']:
                    op_str = f'{k[-1]}='
                    op = OptionOp.get(op_str)
                    k = k[:-1].strip()
                else:
                    op = OptionOp.REPLACE
                    k = k.strip()
                v = parse_value(v.strip())
                for active_phase in arg_affected_phases:
                    active_phase.push_opts({k: Op(op, v)})
            else:
                for active_phase in arg_affected_phases:
                    active_phase.pop_opts([override])

            file_operations_are_dirty = True

        else:
            arg_affected_phases = []

            if file_operations_are_dirty:
                WorkingSet.main_phase.compute_file_operations_in_dependencies()
                file_operations_are_dirty = False

            if ':' in arg:
                phase_labels, arg = arg.split(':', 1)
                arg_affected_phases = get_phases(phase_labels)
            else:
                arg_affected_phases = affected_phases

            arg = WorkingSet.action_aliases.get(arg, [arg])[0]
            action = Action(arg)
            for active_phase in arg_affected_phases:
                active_phase.do(action)

            res = action.run()
            if res.failed():
                return ReturnCode.ACTION_FAILED.value

            actions_done.append(action.name)

        idx += 1

    if len(actions_done) == 0:
        WorkingSet.main_phase.compute_file_operations_in_dependencies()
        action = Action(WorkingSet.default_action)
        for active_phase in affected_phases:
            active_phase.do(action)

        res = action.run()
        if res.failed():
            return ReturnCode.ACTION_FAILED.value

    return ReturnCode.SUCCEEDED.value

if __name__ == '__main__':
    main()
