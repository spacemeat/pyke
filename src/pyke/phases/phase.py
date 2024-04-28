'''
This is the base Phase class for all other Phase types. All the base functionality
is contained herein.
'''

from copy import deepcopy
from functools import partial
import inspect
from os.path import relpath
from pathlib import Path
import sys
from typing import Type, TypeVar, TypeAlias, Iterable, Any
from typing_extensions import Self

from ..action import (Action, ResultCode, Step, Result,
                      FileData, FileOperation, PhaseFiles)
from ..options import Options, OptionOp
from ..utilities import (ensure_list, WorkingSet, do_shell_command, uniquify_list,
                         determine_color_support, ansi_colors, set_color,
                         CircularDependencyError)

T = TypeVar('T')
Steps: TypeAlias = list[Step] | Step | None

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
        self.options = Options()

        project_root = WorkingSet.makefile_dir
        color_table_ansi_24bit = deepcopy(ansi_colors['colors_24bit'])
        color_table_ansi_8bit = deepcopy(ansi_colors['colors_8bit'])
        color_table_ansi_named = deepcopy(ansi_colors['colors_named'])
        color_table_none = deepcopy(ansi_colors['colors_none'])
        supported_terminal_colors = determine_color_support()

        self.options |= {
            # The name of the phase. You should likely override this.
            'name': '',
            # The group name of the phase. Informed by its nearest dependent project phase.
            'group': '',
            # The verbosity of reporting. 0 just reports the phase by name; 1 reports the phase's
            # interpolated options; 2 reports the raw and interpolated options.
            'report_verbosity': 2,
            # Whether to print full paths, or relative to $CWD when reporting.
            'report_relative_paths': True,
            # The verbosity of non-reporting actions. 0 is silent, unless there are errors; 1 is an
            # abbreviated report; 2 is a full report with all commands run.
            'verbosity': 0,
            # Interpolated value for None.
            'none': None,
            # Interpolated value for True.
            'true': True,
            # Interpolated value for False.
            'false': False,
            # This is an anchor directory for other directories to relate to when referencing
            # required project inputs like source files.
            'project_anchor': project_root,
            # This is an anchor directory for other directories to relate to when referencing
            # generated build artifacts like object files or executables.
            'gen_anchor': project_root,
            # Top-level build directory.
            'build_dir': 'build',
            'build_anchor': '{gen_anchor}/{build_dir}',
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
            # Routes action invocations to action calls.
            'action_map': {},
            # Select the system build tools. gnu|clang
            'toolkit': 'gnu',
            'target_os_gnu': 'posix',
            'target_os_clang': 'posix',
            ##'target_os_visualstudio': 'windows',
            'target_os': '{target_os_{toolkit}}',
            # Sets debug or release build. You can add your own; see the README.
            'kind': 'debug',
            # Project version major value
            'version_major': '0',
            # Project version minor value
            'version_minor': '0',
            # Project version patch value
            'version_patch': '0',
            # Project version build value
            'version_build': '0',
            'version_mm': 'v{version_major}.{version_minor}',
            'version_mmp': 'v{version_major}.{version_minor}.{version_patch}',
            'version_mmpb': 'v{version_major}.{version_minor}.{version_patch}.{version_build}',
            # Dotted-values version string.
            'version': '{version_mmp}',
        }
        self.options |= (options or {})

        self.is_project_phase = False

        if dependencies is None:
            dependencies = []
        dependencies = ensure_list(dependencies)
        self.dependencies = []
        for dep in dependencies:
            self.depend_on(dep)

        self.files: PhaseFiles

    def __repr__(self):
        return self.name

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
        ''' Returns whether dep_to_find is in the dependency tree for this phase. '''
        try:
            idx = self.dependencies.index(dep_to_find)
            return self.dependencies[idx]
        except ValueError:
            for dep in self.dependencies:
                phase = dep.find_in_dependency_tree(dep_to_find)
                if phase is not None:
                    return phase
            return None

    def depend_on(self, new_deps: Self | list[Self]):
        ''' Sets a dependency phase for this phase. Must not be a phase which does not
        depend on this phase already (no circular references allowed). '''
        new_deps = ensure_list(new_deps)
        for new_dep in new_deps:
            if new_dep.find_in_dependency_tree(self) is not None:
                raise CircularDependencyError(
                    f'Attempt to set a circular dependency {new_dep.opt_str("name")} '
                    f'to phase {self.name}. Not cool.')
            self.dependencies.append(new_dep)

    def clone(self, options: dict | None = None,
              dependencies = None):
        ''' Returns a clone of this instance. The clone has the same
        options (also copied) but its own dependencies and action
        results state. '''
        obj = type(self)(None, dependencies)
        obj.options = self.options.clone()
        obj.options |= (options or {})
        return obj

    def propagate_group_names(self, group_name: str):
        ''' Cascades project names to unset group names in dependency phases.'''
        if self.is_project_phase:
            group_name = self.name
            self.name = 'project'
        if not self.opt_str('group'):
            self.push_opts({'group': group_name})
        else:
            group_name = self.opt_str('group')
        for phase in self.dependencies:
            phase.propagate_group_names(group_name)

    def patch_options_in_dependencies(self):
        ''' Opportunity for phases to fix up options before running file operations.'''
        for dep in list(self.enumerate_dependencies()):
            dep.patch_options()

    def patch_options(self):
        ''' Fixups run before file operations.'''

    def compute_file_operations_in_dependencies(self):
        ''' Compute file operations dwon the dependency hierarchy.'''
        for dep in list(self.enumerate_dependencies()):
            dep.files = PhaseFiles()
            dep.compute_file_operations()

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output files.'''

    def record_file_operation(self, input_files: list[FileData] | FileData | None,
                              output_files: list[FileData] | FileData | None, step_name: str):
        ''' Record a file transform this phase can perform.'''
        self.files.record(FileOperation(input_files, output_files, step_name))

    def get_direct_dependency_output_files(self, file_type: str):
        ''' Returns all the generated files of a type by any direct dependency phases.'''
        return [file_data
            for dep in self.dependencies
            for file_data in dep.files.get_output_files(file_type)]

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

    def push_opts(self, overrides: dict,
                  include_deps: bool = False, include_project_deps: bool = False):
        ''' Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line. '''
        self.options |= overrides
        if include_deps:
            for dep in self.dependencies:
                if not dep.is_project_phase or include_project_deps:
                    dep.push_opts(overrides, include_deps, include_project_deps)

    def pop_opts(self, keys: list[str],
                  include_deps: bool = False, include_project_deps: bool = False):
        ''' Removes pushed option overrides. '''
        if include_deps:
            for dep in reversed(self.dependencies):
                if not dep.is_projet_phase or include_project_deps:
                    dep.pop_opts(keys, include_deps, include_project_deps)
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

    def make_cmd_delete_file(self, path: Path):
        ''' Returns an appropriate command for deleting a file. '''
        return f'rm {str(path)}'

    def c(self, color):
        ''' Returns a named color.'''
        return set_color(self.opt_dict('colors_dict'), color)

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

    def color_phase(self, phase: 'Phase'):
        ''' Returns a colorized phase name and type.'''
        phase_type = type(phase).__name__
        return (f'{self.c("phase_lt")}{phase.full_name}{self.c("phase_dk")} '
                f'({self.c("phase_lt")}{phase_type}{self.c("phase_dk")}){self.c("off")}')

    def color_file_type(self, file_type: str):
        ''' Returns a colorized file type.'''
        return f'{self.c("file_type_lt")}{file_type}{self.c("off")}'

    def format_file_data(self, file: FileData):
        ''' Formats a FileData object for reporting.'''
        phase_name = (self.color_phase(file.generating_phase)
                      if file.generating_phase is not None else '')
        s = (f'    {self.color_path(file.path)}{self.c("step_dk")} - '
             f'{self.c("file_type_dk")}type: {self.color_file_type(file.file_type)}')
        if file.generating_phase is not None:
            s += (f'{self.c("step_dk")} - {self.c("phase_dk")}generated by: {phase_name}'
                  f'{self.c("off")}')
        else:
            s += f'{self.c("step_dk")} - {self.c("phase_dk")}(extant file){self.c("off")}'
        return s

    def color_file_step_name(self, step_name: str):
        ''' Colorize a FileOperation step name for reporting.'''
        return f'{self.c("step_lt")}{step_name}{self.c("off")}'

    def format_action(self, action_name: str):
        ''' Formats an action name for reporting.'''
        s = f'{self.c("action_dk")}action: {self.c("action_lt")}{action_name}{self.c("off")}'
        return s

    def format_phase(self, phase: Self):
        ''' Formats an action name for reporting.'''
        s = (f'{self.c("phase_dk")}phase: {self.color_phase(phase)}{self.c("phase_dk")}:'
             f'{self.c("off")}')
        return s

    def report_phase(self, action: str, phase: Self):
        ''' Prints a phase summary. '''
        print (f'{self.format_action(action)}{self.c("action_dk")} - '
               f'{self.format_phase(phase)}', end = '')

    def report_error(self, action: str, phase: Self, err: str):
        ''' Print an error string to the console in nice, bright red. '''
        self.report_phase(action, phase)
        print (f'\n{err}')

    def report_action_phase_start(self, action: str, phase: Self):
        ''' Reports on the start of an action. '''
        if self.opt_int('verbosity') > 0:
            self.report_phase(action, phase)
            print ('')

    def report_action_phase_end(self, result: ResultCode):
        ''' Reports on the start of an action. '''
        verbosity = self.opt_int('verbosity')
        if verbosity > 1 and result.succeeded():
            print (f'        {self.c("action_dk")}... action {self.c("success")}succeeded'
                   f'{self.c("off")}')
        elif verbosity > 0 and result.failed():
            print (f'        {self.c("action_dk")}... action {self.c("fail")}failed{self.c("off")}')

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
        if result.code.succeeded():
            if verbosity > 0:
                print (f'{self.c("step_dk")} - {self.c("success")}{result.code.view_name}'
                       f'{self.c("step_dk")}{self.c("off")}')
        elif result.code.failed():
            if verbosity > 0:
                print (f'{self.c("step_dk")} - {self.c("fail")}{result.code.view_name}'
                       f'{self.c("step_dk")}{self.c("off")}')
            if result.notes:
                print (f'{result.notes}', file=sys.stderr)

    def do(self, action: Action):
        ''' Performs an action, such as 'build' or 'run'. '''

        # TODO: This is where a pre-action step should be performed, if any. Good place for 
        # project hooks like remote build launches, container setups, etc.

        if action.set_phase(self) != ResultCode.NOT_YET_RUN:
            return

        action_methods = []
        if routes := self.opt_dict('action_map').get(action.name):
            routes = ensure_list(routes)
            for route in routes:
                method = getattr(self, 'do_action_' + route, None)
                action_methods.append(method)
        else:
            method = getattr(self, 'do_action_' + action.name, None)
            action_methods.append(method)

        for method in action_methods:
            if method:
                method(action)

    def do_step_delete_file(self, action: Action, depends_on: Steps, path: Path) -> Step:
        ''' Perfoems a file deletion operation as an action step. '''
        def act(cmd: str, path: Path) -> Result:
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if path.exists():
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = self.make_cmd_delete_file(path)
        step = Step('delete file', depends_on, [path], [],
                             partial(act, cmd=cmd, path=path), cmd)
        action.set_step(step)
        return step

    def do_step_delete_directory(self, action: Action, depends_on: Steps, direc: Path) -> Step:
        ''' Perfoems a file deletion operation as an action step. '''
        def act(cmd: str, direc: Path) -> Result:
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if direc.exists():
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = f'rm -r {direc}'
        step = Step('delete directory', depends_on, [direc], [],
                             partial(act, cmd=cmd, direc=direc), cmd)
        action.set_step(step)
        return step

    def do_action_report_options(self, action: Action):
        ''' This gives a small description of the phase. '''
        report = ''
        report_verbosity = self.opt_int('report_verbosity')
        self.report_action_phase_start(action.name, self)

        if report_verbosity >= 1:
            opts_str = ''
            for k in self.options.keys():
                vu = self.options.get(k, False)
                vi = self.options.get(k)

                assert isinstance(vu, list)

                indent = 0
                opts_str = ''.join((opts_str, f'{self.c("key")}{k}: '))
                last_replace_idx = len(vu) - next(i for i, e in enumerate(reversed(vu))
                    if e.operator == OptionOp.REPLACE) - 1
                if report_verbosity >= 2:
                    for i, vue in enumerate(vu):
                        color = (self.c("val_uninterp_dk") if i < last_replace_idx
                                 else self.c("val_uninterp_lt"))
                        op = vue.operator.value
                        indent = 0 if i == 0 else len(k) - len(op) + 3
                        opts_str = ''.join(
                            (opts_str, f'{" " * indent}{color}{op} {vue.value}{self.c("off")}\n'))
                    indent = len(k) + 1
                else:
                    indent = 0

                opts_str = ''.join((opts_str,
                                    f'{" " * indent}{self.c("val_interp")}-> {vi}\n'))

            report += f'{opts_str}{self.c("off")}'
        print (report)

    def do_action_report_files(self, action: Action):
        ''' Prints the cmoputed file operations for each phase.'''
        self.report_action_phase_start(action.name, self)
        for file_op in self.files.operations:
            print (f'  {self.color_file_step_name(file_op.step_name)}{self.c("step_dk")}:'
                   f'{self.c("off")}')
            for file in file_op.input_files:
                print (self.format_file_data(file))
            print (f'    {self.c("step_dk")}->{self.c("off")}')
            for file in file_op.output_files:
                print (self.format_file_data(file))
        print ('')

    def do_action_report_actions(self, action: Action):
        ''' Prints the available actions defined in all phases and their hierarchies.'''
        self.report_action_phase_start(action.name, self)
        methods = []
        for superclass in type(self).__mro__:
            methods.extend(inspect.getmembers(superclass, predicate=inspect.isfunction))
        endl = '\n'
        methods = [f"{endl}  {self.format_action(method[0][len('do_action_'):])}"
                   for method in methods if method[0].startswith('do_action_')]
        print (f'{self.format_phase(self)} {"".join(uniquify_list(methods))}')

    def do_action_clean(self, action: Action):
        ''' Cleans all object paths this phase builds. '''
        for file in self.files.get_output_files():
            if file.file_type != 'dir':
                self.do_step_delete_file(action, None, file.path)

    def do_action_clean_build_directory(self, action: Action):
        ''' Wipes out the build directory. '''
        self.do_step_delete_directory(action, None, Path(self.opt_str("build_anchor")))
