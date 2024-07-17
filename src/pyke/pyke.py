'''
Python library for building software.
'''

# pylint: disable=broad-exception-caught, too-few-public-methods

# TODO: Lots of good goals outlined here:  https://www.youtube.com/watch?v=Sh3uayB9kHs

from enum import Enum
import importlib.util
import importlib.machinery
import os
from pathlib import Path
import sys
import traceback

from . import __version__
from .action import Action
from .config import Configurator
from .options import OptionOp, Op
from .options_parser import parse_value
from .phases.phase import Phase
from .phases.project import ProjectPhase
from .utilities import (PhaseNotFoundError, PykeMakefileNotFoundError, PykeMakefileNotLoadedError,
                        PykeException, ensure_list)

class ExecutorStack:
    ''' Holds a stack of executors for recursive loading. '''
    executors = []

    @classmethod
    def push(cls, executor):
        ''' Add an executor for loading through get_main_phase(). '''
        cls.executors.append(executor)

    @classmethod
    def pop(cls):
        ''' Remove an executor once loaded. '''
        del cls.executors[-1]

def get_main_phase() -> Phase:
    ''' Returns the main project created for the makefile.'''
    if len(ExecutorStack.executors) == 0:
        raise PhaseNotFoundError('No main phase found. Seems unlikely, but there it is.')
    return ExecutorStack.executors[-1].root_phase

class ReturnCode(Enum):
    ''' Encoded return code for program exit.'''
    SUCCEEDED = 0
    MAKEFILE_NOT_FOUND = 1
    MAKEFILE_DID_NOT_LOAD = 2
    INVALID_ARGS = 3
    ACTION_FAILED = 4

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
-m, --makefile: Specifies the makefile (pyke file) to be run. Actions are
    performed relative to the makefile's directory, unless an option override
    (-o gen_anchor=dir/to/gen) is given, in which case they are performed
    relative to the given anchor directory. If no -m argument is given, pyke
    will look for and run ./make.py.
-n, --noconfig: Specifies that the pyke-config.json file adjacent to the
    makefile should not be loaded.
-c, --report-config: Prints the full configuration combined from all loaded
    config files, and exits.

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

class PykeExecutor:
    ''' Create a pyke run environment. Loads and fully prepares a pyke file. Make one instance
    of this for each Pyke makefile to load. 
    makefile: Must be a full directory or path to a makefile.
    load_makefile_config: Whether to load the makefile's corresponding config file.'''
    def __init__(self, makefile: Path, load_makefile_config: bool = True):
        self.makefile = makefile
        self.load_makefile_config = load_makefile_config
        self.config = Configurator()
        self.root_phase: Phase
        self.args = []

    def load(self):
        ''' Load and run a makefile by relative path to the makefile directory.'''
        ExecutorStack.push(self)
        self._load_default_config()
        self._load_and_run_makefile()
        self._propagate_group_names()
        self._uniquify_phase_names()
        self._patch_options_in_dependencies()
        self._process_config_args()
        return self.root_phase

    def process_command_line_args(self, cmdline_args: list[str]):
        ''' Process command line args. '''
        args = []
        for arg in cmdline_args:
            pure_arg = self.config.argument_aliases.get(arg, [arg])
            args.extend(pure_arg)
        self._process_args(args, True)

    def _load_default_config(self):
        ''' Loads the default config and home config. '''
        self.config.load_from_default_config()
        self.config.load_from_home_config()

    def _load_and_run_makefile(self):
        make_path = Path(self.makefile)
        if make_path.is_dir():
            make_path = make_path / 'make.py'

        makefile_dir = make_path.parent

        if self.load_makefile_config:
            self.config.load_from_makefile_dir(makefile_dir)

        root_phase_name = (make_path.parent.name if
            make_path.name == 'make.py'
            else make_path.stem)
        self.root_phase = ProjectPhase({
            'name': root_phase_name,
            'project_root_dir': str(makefile_dir)})

        self._run_makefile(make_path)

    def _run_makefile(self, pyke_path):
        ''' Loads and runs the user-created make file.'''
        cache_make = self.config.cache_makefile_module
        if pyke_path.exists():
            try:
                old_dont_write_bytecode = sys.dont_write_bytecode
                sys.dont_write_bytecode = not cache_make
                spec = importlib.util.spec_from_file_location('pyke', pyke_path)
                if spec:
                    module = importlib.util.module_from_spec(spec)
                    loader = spec.loader
                    if loader:
                        loader.exec_module(module)
                        sys.dont_write_bytecode = old_dont_write_bytecode
                        return
                    raise PykeException('no loader')
                raise PykeException('no spec')
            except Exception as e:
                raise PykeMakefileNotLoadedError(f'"{pyke_path}" could not be loaded.') from e
        else:
            raise PykeMakefileNotFoundError(f'"{pyke_path}" was not found.')

    def _propagate_group_names(self):
        ''' Cascades project names to group names in dependency phases.'''
        if self.root_phase:
            self.root_phase.propagate_group_names('')

    def _uniquify_phase_names(self):
        ''' Ensure phase names are unique within groups.'''
        if not self.root_phase:
            return

        names = {}
        for phase in self.root_phase.iterate_dep_tree():
            fullname = phase.full_name
            if fullname in names:
                count, phase_list = names[fullname]
                if phase not in phase_list:
                    phase_list.append(phase)
                    names[fullname] = (count + 1, phase_list)
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

    def _patch_options_in_dependencies(self):
        if not self.root_phase:
            return

        self.root_phase.patch_options_in_dependencies()

    def _get_phases(self, labels: list[str] | str) -> list[Phase]:
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
        if not self.root_phase:
            return []

        phases = []
        labels = ensure_list(labels)
        for label in labels:
            if '.' not in label:
                label = f'{self.root_phase.name}.{label}'
            if label.startswith('.'):
                label = f'{self.root_phase.name}{label}'
            group_phase_label = label.split('.', 1)
            grouplabel, namelabel = group_phase_label
            for phase in self.root_phase.iterate_dep_tree():
                if grouplabel in ['@', phase.group]:
                    if namelabel in ['@', phase.name]:
                        phases.append(phase)
        return phases

    def _process_config_args(self):
        args = []
        for arg in self.config.default_arguments:
            pure_arg = self.config.argument_aliases.get(arg, [arg])
            args.extend(pure_arg)
        self._process_args(args)

    def _process_args(self, args: list[str], run_default_action: bool = False):
        actions_done = []
        file_operations_are_dirty = True

        affected_phases = '@.@'
        idx = 0
        while idx < len(args):
            arg = args[idx]
            if arg.startswith('-p') or arg == '--phases':
                if len(arg) > 2:
                    phases = arg[2:]
                else:
                    idx += 1
                    phases = args[idx]
                affected_phases = phases

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
                    arg_affected_phases = phase_labels
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
                    for active_phase in self._get_phases(arg_affected_phases):
                        active_phase.push_opts({k: Op(op, v)})
                else:
                    for active_phase in self._get_phases(arg_affected_phases):
                        active_phase.pop_opts([override])

                file_operations_are_dirty = True
            else:
                arg_affected_phases = []

                if file_operations_are_dirty:
                    self.root_phase.compute_file_operations_in_dependencies()
                    file_operations_are_dirty = False

                if ':' in arg:
                    phase_labels, arg = arg.split(':', 1)
                    arg_affected_phases = phase_labels
                else:
                    arg_affected_phases = affected_phases

                arg = self.config.action_aliases.get(arg, [arg])[0]
                action = Action(arg)
                for active_phase in self._get_phases(arg_affected_phases):
                    active_phase.do(action)

                res = action.run()
                if res.failed():
                    return ReturnCode.ACTION_FAILED.value

                actions_done.append(action.name)

            idx += 1

        if run_default_action and len(actions_done) == 0:
            self.root_phase.compute_file_operations_in_dependencies()
            action = Action(self.config.default_action)
            for active_phase in self._get_phases(affected_phases):
                active_phase.do(action)

            res = action.run()
            if res.failed():
                return ReturnCode.ACTION_FAILED.value

        return ReturnCode.SUCCEEDED.value

def run_makefile(make_file, load_makefile_config: bool = True):
    ''' Load and run a makefile outside of the project_phase. '''
    current_dir = os.getcwd()
    exe = PykeExecutor(Path(current_dir) / make_file, load_makefile_config)
    return exe.load()


def main():
    '''Entrypoint for pyke.'''
    current_dir = os.getcwd()
    make_file = 'make.py'
    load_makefile_config = True

    idx = 1
    while idx < len(sys.argv):
        arg = sys.argv[idx]

        if arg in ['-v', '--version']:
            print_version()
            return ReturnCode.SUCCEEDED.value

        if arg in ['-h', '--help']:
            print_help()
            return ReturnCode.SUCCEEDED.value

        if arg.startswith('-m') or arg == '--makefile':
            make_file = ''
            if len(arg) > 2:
                make_file = sys.argv[idx][2:]
            else:
                idx += 1
                make_file = sys.argv[idx]
            idx += 1
            continue

        if arg in ['-n', '--noconfig']:
            load_makefile_config = False
            idx += 1
            continue

        break

    exe = PykeExecutor(Path(current_dir) / make_file, load_makefile_config)

    try:
        exe.load()
    except PykeMakefileNotFoundError as e:
        print (e)
        sys.exit(ReturnCode.MAKEFILE_NOT_FOUND.value)

    except PykeMakefileNotLoadedError as e:
        print (e)
        traceback.print_exc()
        sys.exit(ReturnCode.MAKEFILE_DID_NOT_LOAD.value)

    #WorkingSet.main_phase = main_phase

    #propagate_group_names()
    #uniquify_phase_names()
    #main_phase.patch_options_in_dependencies()

    return exe.process_command_line_args(sys.argv)
'''
    actions_done = []
    file_operations_are_dirty = True

    args = []
    for arg in [*exe.config.default_arguments, *sys.argv[idx:]]:
        args.extend(exe.config.argument_aliases.get(arg, [arg]))

    affected_phases = exe.get_phases('@.@')

    idx = 0
    while idx < len(args):
        arg = args[idx]

        if arg in ['--makefile', '-n', '--noconfig'] or arg.startswith('-m'):
            print (f'{arg} must precede any of -p (--phase), -o (--override), '
                   '-c (--report_config), or any action arguments.')
            return ReturnCode.INVALID_ARGS.value

        if arg in ['-v', '--version']:
            print_version()
            return ReturnCode.SUCCEEDED.value

        if arg in ['-h', '--help']:
            print_help()
            return ReturnCode.SUCCEEDED.value

        if arg in ['-c', '--report_config']:
            print(exe.config.report())
            return ReturnCode.SUCCEEDED.value

        if arg.startswith('-p') or arg == '--phases':
            if len(arg) > 2:
                phases = arg[2:]
            else:
                idx += 1
                phases = args[idx]
            affected_phases = exe.get_phases(phases)

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
                arg_affected_phases = exe.get_phases(phase_labels)
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
                main_phase.compute_file_operations_in_dependencies()
                file_operations_are_dirty = False

            if ':' in arg:
                phase_labels, arg = arg.split(':', 1)
                arg_affected_phases = exe.get_phases(phase_labels)
            else:
                arg_affected_phases = affected_phases

            arg = exe.config.action_aliases.get(arg, [arg])[0]
            action = Action(arg)
            for active_phase in arg_affected_phases:
                active_phase.do(action)

            res = action.run()
            if res.failed():
                return ReturnCode.ACTION_FAILED.value

            actions_done.append(action.name)

        idx += 1

    if len(actions_done) == 0:
        main_phase.compute_file_operations_in_dependencies()
        action = Action(exe.config.default_action)
        for active_phase in affected_phases:
            active_phase.do(action)

        res = action.run()
        if res.failed():
            return ReturnCode.ACTION_FAILED.value

    return ReturnCode.SUCCEEDED.value
'''
if __name__ == '__main__':
    main()
