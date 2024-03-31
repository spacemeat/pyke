'''
This is the base Phase class for all other Phase types. All the base functionality
is contained herein.
'''

from os.path import relpath
from pathlib import Path
import sys
from typing import Type, TypeVar, Iterable
from typing_extensions import Self

from ..action import (Action, ResultCode, Step,
                      FileData, FileOperation, PhaseFiles)
from .. import ansi as a
from ..options import Options, OptionOp
from ..utilities import (ensure_list, WorkingSet, #set_color as c,
                         CircularDependencyError, ProjectPhaseDependencyError)

T = TypeVar('T')

# TODO: Auto-detect terminal color capabilities

class Phase:
    '''
    Serves as the base class for a derived PykePhase. Each derived 
    phase represents a relationship between inputs and outputs of 
    a build process. Each phase can support multiple actions such 
    as cleaning, building, running, archiving, etc. Some phases
    only have one obvious action to support; others might be
    referenced as dependencies of other phases. (Think phases that
    build objects from source as dependencies of a phase that builds
    a binary from objects.)

    Pyke comes built-in with numerous useful phase classes, and users
    can define their own to support bespoke processes.
    '''
    def __init__(self, options: dict | None = None,
                 dependencies: Self | list[Self] | None = None):
        self.phase_names = {}
        self.options = Options()
        self.options |= {
            'name': '',
            'report_verbosity': 2,
            'report_relative_paths': True,
            'verbosity': 0,
            'project_anchor': WorkingSet.makefile_dir,
            'gen_anchor': WorkingSet.makefile_dir,
            'simulate': False,
            'colors_24bit': {
                'off':              {'form': 'named', 'off': [] },
                'success':          {'form': 'rgb24', 'fg': [0x33, 0xaf, 0x55] },
                'fail':             {'form': 'rgb24', 'fg': [0xff, 0x33, 0x33] },
                'phase_lt':         {'form': 'rgb24', 'fg': [0x33, 0x33, 0xff] },
                'phase_dk':         {'form': 'rgb24', 'fg': [0x23, 0x23, 0x7f] },
                'step_lt':          {'form': 'rgb24', 'fg': [0x33, 0xaf, 0xaf] },
                'step_dk':          {'form': 'rgb24', 'fg': [0x23, 0x5f, 0x5f] },
                'shell_cmd':        {'form': 'rgb24', 'fg': [0x31, 0x31, 0x32] },
                'key':              {'form': 'rgb24', 'fg': [0xff, 0x8f, 0x23] },
                'val_uninterp_dk':  {'form': 'rgb24', 'fg': [0x5f, 0x13, 0x5f] },
                'val_uninterp_lt':  {'form': 'rgb24', 'fg': [0xaf, 0x23, 0xaf] },
                'val_interp':       {'form': 'rgb24', 'fg': [0x33, 0x33, 0xff] },
                'token_type':       {'form': 'rgb24', 'fg': [0x33, 0xff, 0xff] },
                'token_value':      {'form': 'rgb24', 'fg': [0xff, 0x33, 0xff] },
                'token_depth':      {'form': 'rgb24', 'fg': [0x33, 0xff, 0x33] },
                'path_lt':          {'form': 'rgb24', 'fg': [0x33, 0xaf, 0xaf] },
                'path_dk':          {'form': 'rgb24', 'fg': [0x23, 0x5f, 0x5f] },
            },
            'colors_named': {
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
                'val_uninterp_dk':  {},
                'val_uninterp_lt':  {},
                'val_interp':       {},
                'token_type':       {},
                'token_value':      {},
                'token_depth':      {},
                'path_lt':          {},
                'path_dk':          {},
            },
            'colors': '{colors_24bit}',
        }
        self.options |= (options or {})

        assert isinstance(options, dict)
        self.is_project_phase = False
        self.last_action_ordinal = -1
        self.last_action_result = None

        self.override_project_dependency_options = False

        if dependencies is None:
            dependencies = []
        dependencies = ensure_list(dependencies)
        self.dependencies = []
        for dep in dependencies:
            self.set_dependency(dep)

        self.files = None

    def record_file_operation(self, input_files: list[FileData] | FileData | None,
                              output_files: list[FileData] | FileData | None, step_name: str):
        ''' Record a file transform this phase can perform.'''
        self.files.record(FileOperation(input_files, output_files, step_name))

    def get_dependency_output_files(self, file_type: str):
        ''' Returns all the generated files of a type by this phase or any dependency phases.'''
        deps = list(self.enumerate_dependencies())[:-1]
        return [file_data
            for dep in deps
            for file_data in dep.files.get_output_files(file_type)]

    def compute_file_operations_in_dependencies(self):
        ''' Compute file operations dwon the dependency hierarchy.'''
        for dep in list(self.enumerate_dependencies()):
            dep.files = PhaseFiles()
            dep.compute_file_operations()

    def compute_file_oerations(self):
        ''' Subclasses must implement this to record operations.'''

    @property
    def name(self):
        ''' Quick property to get the name option.'''
        return self.opt_str('name')

    @name.setter
    def name(self, value):
        ''' Quick property to set the name options.'''
        self.push_opts({'name': value})

    def push_opts(self, overrides: dict,
                  include_deps: bool = False, include_project_deps: bool = False):
        '''
        Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line.
        '''
        self.options |= overrides
        if include_deps:
            for dep in self.dependencies:
                if not dep.is_project_phase or include_project_deps:
                    dep.push_opts(overrides, include_deps, include_project_deps)

    def pop_opts(self, keys: list[str],
                  include_deps: bool = False, include_project_deps: bool = False):
        '''
        Removes pushed option overrides.
        '''
        if include_deps:
            for dep in reversed(self.dependencies):
                if not dep.is_projet_phase or include_project_deps:
                    dep.pop_opts(keys, include_deps, include_project_deps)
        for key in keys:
            self.options.pop(key)

    def opt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        '''
        if overrides:
            self.options |= overrides
        val = self.options.get(key, interpolate)
        if overrides:
            for k in overrides.keys():
                self.options.pop(k)
        return val

    def opt_t(self, obj_type: Type[T], key: str, overrides: dict | None = None,
              interpolate: bool = True) -> T:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a tuple.
        '''
        val = self.opt(key, overrides, interpolate)
        assert isinstance(val, obj_type)
        return val

    def opt_iter(self, key: str, overrides: dict | None = None,
                 interpolate: bool = True) -> Iterable:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a tuple.
        '''
        return self.opt_t(Iterable, key, overrides, interpolate)

    def opt_bool(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> bool:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a bool.
        '''
        return self.opt_t(bool, key, overrides, interpolate)

    def opt_int(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> int:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be an int.
        '''
        return self.opt_t(int, key, overrides, interpolate)

    def opt_float(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> float:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a float.
        '''
        return self.opt_t(float, key, overrides, interpolate)

    def opt_str(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> str:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a string.
        '''
        return self.opt_t(str, key, overrides, interpolate)

    def opt_tuple(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> tuple:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a tuple.
        '''
        return self.opt_t(tuple, key, overrides, interpolate)

    def opt_list(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> list:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a list.
        '''
        return self.opt_t(list, key, overrides, interpolate)

    def opt_set(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> set:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a set.
        '''
        return self.opt_t(set, key, overrides, interpolate)

    def opt_dict(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> dict:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a dict.
        '''
        return self.opt_t(dict, key, overrides, interpolate)

    def __repr__(self):
        return str(self.name)

    def clone(self, options: dict | None = None):
        '''
        Returns a clone of this instance. The clone has the same
        options (also copied) but its own dependencies and action
        results state.
        '''
        obj = type(self)({})
        obj.options = self.options.clone()
        obj.options |= (options or {})
        return obj

    def enumerate_dependencies(self):
        ''' Enumerates all the dependencies in depth-first order.'''
        for dep in self.dependencies:
            yield from dep.enumerate_dependencies()
        yield self

    def find_dependency_by_name(self, name: str):
        ''' Finds the dependency (including self) by name.'''
        for dep in self.enumerate_dependencies():
            if dep.opt_str('name') == name:
                return dep
        return None

    def find_in_dependency_tree(self, dep_to_find: Self):
        '''
        Returns whether dep_to_find is in the dependency tree for 
        this phase.
        '''
        try:
            idx = self.dependencies.index(dep_to_find)
            return self.dependencies[idx]
        except ValueError:
            for dep in self.dependencies:
                phase = dep.find_in_dependency_tree(dep_to_find)
                if phase is not None:
                    return phase
            return None

    def set_dependency(self, new_deps: Self | list[Self]):
        '''
        Marks a dependency phase for this phase. Must not be a phase
        which does not depend on this phase already (no circular 
        references allowed).
        '''
        new_deps = ensure_list(new_deps)
        for new_dep in new_deps:
            if (not self.is_project_phase and
                new_dep.is_project_phase):
                raise ProjectPhaseDependencyError(
                    f'Attempt by non-project phase "{self.name}" to depend on a '
                    f'project phase "{new_dep.opt_str("name")}.')
            if new_dep.find_in_dependency_tree(self) is not None:
                raise CircularDependencyError(
                    f'Attempt to set a circular dependency {new_dep.opt_str("name")} '
                    f'to phase {self.name}. Not cool.')
            self.dependencies.append(new_dep)

    def c(self, color):
        ''' Returns the ANSI color code for the specified thematic element.'''
        #color_desc = WorkingSet.colors.get(color)
        color_desc = self.opt_dict('colors')[color]
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

    def make_cmd_delete_file(self, path: Path):
        '''
        Returns an appropriate command for deleting a file.
        '''
        return f'rm {str(path)}'

    def do(self, action: Action):
        '''
        Performs an action, such as 'build' or 'run'. 

        First, each dependency phase is called with the same action, depth-first.
        Next, the corresponding 'do_action_<action>' method is called for this
        phase.

        Each invoked action records the phases that run it, to prevent repeat actions
        for phases which are dependents of multiple other phases. This is managed
        internally.
        '''

        for dep in self.dependencies:
            if dep.is_project_phase:
                dep.do(action)

        if self.is_project_phase:
            if action.set_project(self.name) != ResultCode.NOT_YET_RUN:
                return

        for dep in self.dependencies:
            if not dep.is_project_phase:
                dep.do(action)

        if not self.is_project_phase:
            if action.set_phase(self) != ResultCode.NOT_YET_RUN:
                return

        #WorkingSet.report_verbosity = self.opt_int('report_verbosity')
        #WorkingSet.verbosity = self.opt_int('verbosity')
        #if cols := self.opt('colors'):
        #    if isinstance(cols, dict):
        #        WorkingSet.colors = cols

        action_method = getattr(self, 'do_action_' + action.name, None)
        if action_method:
            #report_action_start(action.name, self.name, type(self).__name__)
            action_method(action)
            #report_action_end(action.name, self.name, type(self).__name__)

    def color_path(self, path: Path | str):
        ''' Returns a colorized and possibly CWD-relative version of a path. '''
        if isinstance(path, Path):
            path = str(path)
        if self.opt_bool('report_relative_paths'):
            path = relpath(path)
        path = Path(path)
        return f'{self.c("path_dk")}{path.parent}/{self.c("path_lt")}{path.name}{self.c("off")}'

    def format_path_list(self, paths):
        ''' Returns a colorized path or formatted list notation for a list of paths. '''
        paths = ensure_list(paths)
        if len(paths) == 0:
            return ''
        if len(paths) == 1:
            return self.color_path(paths[0])
        return f'{self.c("path_dk")}[{self.c("path_lt")}...{self.c("path_dk")}]{self.c("off")}'

    def report_phase(self, action: str, phase: str, phase_type: str):
        ''' Prints a phase summary. '''
        print (f'{self.c("phase_dk")}action: {self.c("phase_lt")}{action}{self.c("phase_dk")} '
               f'- phase: {self.c("phase_lt")}{phase}{self.c("phase_dk")} '
               f'({self.c("phase_lt")}{phase_type}{self.c("phase_dk")}):{self.c("off")}', end = '')

    def report_error(self, action: str, phase: str, phase_type: str, err: str):
        ''' Print an error string to the console in nice, bright red. '''
        self.report_phase(action, phase, phase_type)
        print (f'\n{err}')

    def report_action_phase_start(self, action: str, phase: str, phase_type: str):
        ''' Reports on the start of an action. '''
        if self.opt_int('verbosity') > 0:
            self.report_phase(action, phase, phase_type)
            print ('')

    def report_action_phase_end(self, action: str, phase: str, phase_type: str, result: ResultCode):
        ''' Reports on the start of an action. '''
        verbosity = self.opt_int('verbosity')
        if verbosity > 1 and result.succeeded():
            self.report_phase(action, phase, phase_type)
            print (f'{self.c("phase_dk")} ... {self.c("success")}succeeded{self.c("off")}')
        elif verbosity > 0 and result.failed():
            self.report_phase(action, phase, phase_type)
            print (f'{self.c("phase_dk")} ... {self.c("fail")}failed{self.c("off")}')

    def report_step_start(self, step: Step):
        ''' Reports on the start of an action step. '''
        if self.opt_int('verbosity') > 0:
            inputs = self.format_path_list(list(step.inputs))
            outputs = self.format_path_list(list(step.outputs))
            if len(inputs) > 0 or len(outputs) > 0:
                print (f'{self.c("step_lt")}{step.name}{self.c("step_dk")}: {inputs}'
                       f'{self.c("step_dk")} -> {self.c("step_lt")}{outputs}{self.c("off")}',
                       end='')

    def report_step_end(self, step: Step):
        ''' Reports on the end of an action step. '''
        verbosity = self.opt_int('verbosity')
        result = step.result
        if result.code != ResultCode.ALREADY_UP_TO_DATE:
            if verbosity > 1:
                if len(step.command) > 0:
                    print (f'\n{self.c("shell_cmd")}{step.command}{self.c("off")}', end='')
        if result.code.value >= 0:
            if verbosity > 0:
                print (f'{self.c("step_dk")} ({self.c("success")}{result.code.name}'
                       f'{self.c("step_dk")}){self.c("off")}')
        elif result.code.value < 0:
            if verbosity > 0:
                print (f'{self.c("step_dk")} ({self.c("fail")}{result.code.name}'
                       f'{self.c("step_dk")}){self.c("off")}')
            print (f'{result.notes}', file=sys.stderr)

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output fies.'''

    def do_action_report_options(self, action: Action):
        '''
        This gives a small description of the phase.
        '''
        report = ''
        report_verbosity = self.opt_int('report_verbosity')
        if report_verbosity >= 0:
            report = f'phase: {self.name}'

        if report_verbosity >= 1:
            opts_str = ''
            for k in self.options.keys():
                vu = self.options.get(k, False)
                vi = self.options.get(k)

                assert isinstance(vu, list)

                indent = 0
                opts_str = ''.join((opts_str,
                                    f'{self.c("key")}{k}: '))
                last_replace_idx = len(vu) - next(i for i, e in enumerate(reversed(vu))
                    if e[1] == OptionOp.REPLACE) - 1
                if report_verbosity >= 2:
                    for i, vue in enumerate(vu):
                        color = (self.c("val_uninterp_dk") if i < last_replace_idx
                                 else self.c("val_uninterp_lt"))
                        op = vue[1].value if isinstance(vue[1], OptionOp) else ' '
                        indent = 0 if i == 0 else len(k) + 2
                        opts_str = ''.join((opts_str,
                                            f'{" " * indent}{color}{op} {vue[0]}{self.c("off")}\n'))
                    indent = len(k) + 1
                else:
                    indent = 0

                opts_str = ''.join((opts_str,
                                    f'{" " * indent}{self.c("val_interp")}-> {vi}\n'))

            report += f'\n{opts_str}{self.c("off")}'
        print (report)

    def do_action_report_files(self, action: Action):
        ''' Prints the cmoputed file operations for each phase.'''
        print (f'{self.name}:')
        for file_op in self.files.operations:
            print (f'  {file_op.step_name}:')
            for file in file_op.input_files:
                phase_name = file.generating_phase.name if file.generating_phase is not None else ''
                print (f'    {self.color_path(file.path)} - {file.file_type} - {phase_name}')
            print ('    ->')
            for file in file_op.output_files:
                print (f'    {self.color_path(file.path)} - {file.file_type} - '
                       f'{file.generating_phase.name or ""}')
