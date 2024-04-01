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
from .utilities import WorkingSet, MalformedConfigError, ProjectNameCollisionError

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
    def set_default_config():
        WorkingSet.action_aliases = {
            'report-options': 'report_options',
            'opts': 'report_options',
            'report-files': 'report_files',
            'files': 'report_files',
            'c': 'clean',
            'clean-all': '@:clean',
            'ca': '@:clean',
            'clean-build-directory': 'clean_build_directory',
            'clean-build-directory-all': '@:clean_build_directory',
            'cbd': 'clean_build_directory',
            'cbda': '@:clean_build_directory',
            'b': 'build',
            'build-all': '@:build',
            'ba': '@:build',

            '-debug': '-o.@:kind=debug',
            '-debug-all': '-o@,@.@:kind=debug',
            '-v0': '-o@,@.@:verbosity=0',
            '-v1': '-o@,@.@:verbosity=1',
            '-v2': '-o@,@.@:verbosity=2',
        }

    def validate_config(config):
        if not isinstance(config, dict):
            raise MalformedConfigError(f'Config file {file}: Must be a JSON dictonary.')
        if 'aliases' in config:
            aliases = config['aliases']
            if not isinstance(aliases, dict):
                raise MalformedConfigError(f'Config file {file}: "aliases" must be a dictionary.')
            for action, aliases in aliases.items():
                if not isinstance(action, str):
                    raise MalformedConfigError(
                        f'Config file {file}: "aliases/action" key must be a string.')
                if isinstance(aliases, str):
                    aliases = [aliases]
                if (not isinstance(aliases, list) or
                    any(not isinstance(alias, str) for alias in aliases)):
                    raise MalformedConfigError(
                        f'Config file {file}: "aliases/action" value must be a string '
                        'or a list of strings.')
                for alias in aliases:
                    WorkingSet.action_aliases[alias] = action

    set_default_config()

    for direc in list(dict.fromkeys([
            Path.home() / '.config' / 'pyke',
            WorkingSet.makefile_dir,
            Path.cwd()])):
        file = Path(direc) / 'pyke-config.json'
        try:
            with open(file, 'r', encoding='utf-8') as fi:
                config = json.load(fi)
                validate_config(config)
        except (FileNotFoundError, MalformedConfigError):
            pass

def resolve_project_names():
    ''' Uniquify project names, and the phase names within each project.'''
    project_phases = [phase for phase in WorkingSet.main_phase.enumerate_dependencies()
                          if phase.is_project_phase]
    project_names = set()
    for project_phase in project_phases:
        if project_phase.name in project_names:
            raise ProjectNameCollisionError(f'There is already a project named '
                f'{project_phase.name}. Project names must be unique.')
    for phase in project_phases:
        phase.uniquify_phase_names()

class PhaseMap:
    def __init__(self, root_project):
        self.root_project = root_project
        self.project_phases = {
            phase.name: phase
            for phase in root_project.enumerate_dependencies()
            if phase.is_project_phase
        }
        self.non_project_phases = {
            f'{proj_name}.{phase.name}': phase
            for proj_name, proj in self.project_phases.items()
            for phase in proj.enumerate_dependencies()
            if not phase.is_project_phase
        }

    def get_project_phase(self, name: str) -> Phase | None:
        return self.project_phases.get(name, None)

    def get_all_project_phases(self) -> list[Phase]:
        return [v for _, v in self.project_phases.items()]

    def get_non_project_phase(self, name: str) -> Phase | None:
        return self.non_project_phases.get(name, None)

    def get_all_non_project_phases(self) -> list[Phase]:
        return [v for _, v in self.non_project_phases.items()]

    def get_phase_list(self, all_labels: str) -> list[Phase]:
        ''' Gets all the phases according to the following:
        all_labels is a ,-separated least
        for each clause, a label can be in the form x or x.y
        for form x, the value is a project phase name, or *, or ''
            * = all projects
            '' = the main project
        for form x.y, the value is a non-project phase name, or *
            * = all non-project phases under all of the x projects
        So, to select every phase, the right incantation is:
            *, *.*
        '''
        proj_phases = []
        all_named_phases = []
        labels = all_labels.split(',')
        for proj_name in labels:
            proj_name = proj_name.strip()
            nonproj_name = None
            named_phases = []
            if '.' in proj_name:
                proj_name, nonproj_name = proj_name.split('.', 1)
            if proj_name == '':
                proj_phases = [self.root_project]
            elif proj_name == '@':
                proj_phases = self.get_all_project_phases()
            else:
                proj_phases = [self.get_project_phase(proj_name)]

            if nonproj_name == '@':
                named_phases = [v for k, v in self.non_project_phases.items()
                                  for proj_phase in proj_phases
                                if k.startswith(f'{proj_phase.name}.')]
            elif nonproj_name:
                named_phases = [self.get_non_project_phase(
                                f'{project_phase.name}.{nonproj_name}')
                                for project_phase in proj_phases]
            else:
                named_phases = proj_phases
            all_named_phases.extend(named_phases)

        return list(dict.fromkeys(all_named_phases))

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

    WorkingSet.main_phase = ProjectPhase({
        'name': make_path.parent.name if
        make_path.name == 'make.py'
        else make_path.stem})

    run_make_file(make_path, cache_make)
    resolve_project_names()
    phase_map = PhaseMap(WorkingSet.main_phase)

    actions = []
    file_operations_are_dirty = True

    while idx < len(sys.argv):
        arg = sys.argv[idx]

        arg = WorkingSet.action_aliases.get(arg, arg)

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
                override = sys.argv[idx]

            affected_phases = []
            if ':' in override:
                phase_labels, override = override.split(':', 1)
                affected_phases = phase_map.get_phase_list(phase_labels)
            else:
                affected_phases = [WorkingSet.main_phase]

            if '=' in override:
                k, v = override.split('=', 1)
                if k[-1] in ['+', '*', '-', '|', '&', '\\', '^']:
                    op = f'{k[-1]}='
                    k = OptionOp(k[:-1].strip()).name
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
            affected_phases = []
            if ':' in arg:
                phase_labels, arg = arg.split(':', 1)
                affected_phases = phase_map.get_phase_list(phase_labels)
            else:
                affected_phases = [WorkingSet.main_phase]

            if file_operations_are_dirty:
                WorkingSet.main_phase.compute_file_operations_in_dependencies()

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
