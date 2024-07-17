'''
This is the base Phase class for all other Phase types. All the base functionality
is contained herein.
'''

from functools import partial
import inspect
from pathlib import Path
import shlex
from typing import TypeAlias
from typing_extensions import Self

from ..action import (Action, ResultCode, Step, Result,
                      FileData, FileOperation, PhaseFiles)
from ..options import OptionOp
from ..options_owner import OptionsOwner
from ..reporter import Reporter
from ..utilities import (ensure_list, WorkingSet, do_shell_command, uniquify_list,
                         do_interactive_command, CircularDependencyError)

Steps: TypeAlias = list[Step] | Step | None

class Phase(OptionsOwner):
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
        super().__init__()

        project_root = str(WorkingSet.makefile_dir)

        self.options |= {
            # The name of the phase. You should likely override this.
            'name': '',
            # The group name of the phase. Informed by its nearest dependent project phase.
            'group': '',
            # This is the root directory of the project.
            'project_root_dir': project_root,
            # This is an anchor directory for other directories to relate to when referencing
            # required project inputs like source files.
            'project_anchor': '{project_root_dir}',
            # This is an anchor directory for other directories to relate to when referencing
            # generated build artifacts like object files or executables.
            'gen_anchor': '{project_root_dir}',
            # This is an anchor directory for external dependencies such as tarballs or 3rd party
            # repos.
            'external_anchor': '{project_root_dir}',
            # Top-level external dependency packages directory.
            'ext_dir': 'external',
            'external_repos_anchor': '{external_anchor}/{ext_dir}',
            # Top-level build directory.
            'build_dir': 'build',
            'build_anchor': '{gen_anchor}/{build_dir}',
            # Target-specific build directory.
            'build_detail': '{group}.{toolkit}.{kind}',
            'build_detail_anchor': '{build_anchor}/{build_detail}',
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

        self.files = PhaseFiles()
        self.reporter = Reporter(self)

    def __repr__(self):
        return self.full_name

    def iterate_dep_tree(self):
        ''' Enumerates all the dependencies in depth-first order.'''
        for dep in self.dependencies:
            yield from dep.iterate_dep_tree()
        yield self

    def find_dep(self, name: str) -> Self | None:
        ''' Finds the dependency (including self) by name.'''
        for dep in self.iterate_dep_tree():
            if name in (dep.name, dep.full_name):
                return dep
        return None

    def find_dep_object(self, dep_to_match: Self):
        ''' Finds the dependency (including self) by name.'''
        for dep in self.iterate_dep_tree():
            if dep == dep_to_match:
                return dep
        return None

    def depend_on(self, new_deps: Self | list[Self]):
        ''' Sets a dependency phase for this phase. Must not be a phase which does not
        depend on this phase already (no circular references allowed). '''
        new_deps = ensure_list(new_deps)
        for new_dep in new_deps:
            if new_dep.find_dep_object(self) is not None:
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
        for dep in list(self.iterate_dep_tree()):
            dep.patch_options()

    def patch_options(self):
        ''' Fixups run before file operations.'''
        prd = self.opt_str('project_root_dir')
        for dep in self.iterate_dep_tree():
            dep.push_opts({'project_root_dir': prd}, True, True)

    def compute_file_operations_in_dependencies(self):
        ''' Compute file operations dwon the dependency hierarchy.'''
        for dep in self.dependencies:
            dep.compute_file_operations_in_dependencies()
        if len(self.files.operations) == 0:
            self.compute_file_operations()

    def compute_file_operations(self):
        ''' Implement this in any phase that uses input files or generates output files.'''

    def record_file_operation(self, input_files: list[FileData] | FileData | None,
                              output_files: list[FileData] | FileData | None, step_name: str):
        ''' Record a file transform this phase can perform.'''
        self.files.record(FileOperation(input_files, output_files, step_name))

    def get_direct_dependency_output_files(self, file_type: str):
        ''' Returns all the generated files of a type by any direct dependency phases.'''
        return [file_data
            for dep in self.dependencies
            for file_data in dep.files.get_output_files(file_type)]

    def push_opts(self, overrides: dict,
                  include_deps: bool = False, include_project_deps: bool = False):
        ''' Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line. '''
        super().push_opts(overrides)
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
        super().pop_opts(keys)

    def make_cmd_delete_file(self, path: Path):
        ''' Returns an appropriate command for deleting a file. '''
        return f'rm {str(path)}'

    def do(self, action: Action):
        ''' Performs an action, such as 'build' or 'run'. '''

        # TODO: This is where a pre-action step should be performed, if any. Good place for 
        # project hooks like remote build launches, container setups, etc.

        if action.set_phase(self) != ResultCode.NOT_YET_RUN:
            return

        #if len(self.files.operations) == 0:
        #    self.compute_file_operations()

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

    def do_step_create_directory(self, action: Action, depends_on: Steps, new_dir: Path) -> Step:
        '''
        Performs a directory creation operation as an action step.
        '''
        def act(cmd: str, new_dir: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if not new_dir.is_dir():
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = f'mkdir -p {new_dir}'
        step = Step('create directory', depends_on, [], [new_dir],
                             partial(act, cmd=cmd, new_dir=new_dir), cmd)
        action.set_step(step)
        return step

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

    def do_step_run_executable(self, action: Action, depends_on: Steps, exe_path: Path) -> Step:
        ''' Runs the executable as an action step.'''
        def act(cmd: str) -> Result:
            step_notes = None
            res, out, err = do_shell_command(cmd)
            print (f'{out}', end='')
            if res != 0:
                step_result = ResultCode.COMMAND_FAILED
                step_notes = err
            else:
                step_result = ResultCode.SUCCEEDED

            return Result(step_result, step_notes)

        run_dir = self.opt_str('project_anchor')
        cmd = f'cd {run_dir} && {exe_path} {self.opt_str("run_args")}'
        step = Step('run executable', depends_on, [exe_path], [], partial(act, cmd), cmd)
        action.set_step(step)
        return step

    def do_step_run_executable_pty(self, action: Action, depends_on: Steps, exe_path: Path) -> Step:
        ''' Runs the executable as an action step.'''
        def act(cmd: str, exe_path: Path) -> Result:
            cmd_list = shlex.split(cmd)
            step_notes = None
            if exe_path.exists():
                res = do_interactive_command(cmd_list)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.MISSING_INPUT

            return Result(step_result, step_notes)

        cmd = f'{exe_path} {self.opt_str("run_args")}'
        step = Step('run executable', depends_on, [exe_path], [], partial(act, cmd, exe_path), cmd)
        action.set_step(step)
        return step

    def do_action_report_options(self, action: Action):
        ''' This gives a small description of the phase. '''
        report = ''
        report_verbosity = self.opt_int('report_verbosity')
        self.reporter.report_action_phase_start(action.name, type(self).__name__, self.full_name)

        if report_verbosity >= 1:
            opts_str = ''
            for k in self.options.keys():
                vu = self.options.get(k, False)
                vi = self.options.get(k)

                assert isinstance(vu, list)

                indent = 0
                opts_str = ''.join((opts_str, f'{self.reporter.c("key")}{k}: '))
                last_replace_idx = len(vu) - next(i for i, e in enumerate(reversed(vu))
                    if e.operator == OptionOp.REPLACE) - 1
                if report_verbosity >= 2:
                    for i, vue in enumerate(vu):
                        color = (self.reporter.c("val_uninterp_dk") if i < last_replace_idx
                                 else self.reporter.c("val_uninterp_lt"))
                        op = vue.operator.value
                        indent = 0 if i == 0 else len(k) - len(op) + 3
                        opts_str = ''.join(
                            (opts_str, f'{" " * indent}{color}{op} {vue.value}'
                                       f'{self.reporter.c("off")}\n'))
                    indent = len(k) + 1
                else:
                    indent = 0

                opts_str = ''.join((opts_str,
                                    f'{" " * indent}{self.reporter.c("val_interp")}-> {vi}\n'))

            report += f'{opts_str}{self.reporter.c("off")}'
        print (report)

    def do_action_report_files(self, action: Action):
        ''' Prints the cmoputed file operations for each phase.'''
        self.reporter.report_action_phase_start(action.name, type(self).__name__, self.full_name)
        for file_op in self.files.operations:
            print (f'  {self.reporter.color_file_step_name(file_op.step_name)}'
                   f'{self.reporter.c("step_dk")}:{self.reporter.c("off")}')
            for file in file_op.input_files:
                phase = file.generating_phase
                phase_type = type(phase).__name__ if phase else ''
                phase_name = phase.full_name if phase else ''
                print (self.reporter.format_file_data(phase_type, phase_name, file.path,
                                                      file.file_type))
            print (f'    {self.reporter.c("step_dk")}->{self.reporter.c("off")}')
            for file in file_op.output_files:
                phase = file.generating_phase
                phase_type = type(phase).__name__ if phase else ''
                phase_name = phase.full_name if phase else ''
                print (self.reporter.format_file_data(phase_type, phase_name, file.path,
                                                      file.file_type))
        print ('')

    def do_action_report_actions(self, action: Action):
        ''' Prints the available actions defined in all phases and their hierarchies.'''
        self.reporter.report_action_phase_start(action.name, type(self).__name__, self.full_name)
        methods = []
        for superclass in type(self).__mro__:
            methods.extend(inspect.getmembers(superclass, predicate=inspect.isfunction))
        endl = '\n'
        methods = [f"{endl}  {self.reporter.format_action(method[0][len('do_action_'):])}"
                   for method in methods if method[0].startswith('do_action_')]
        print (f'{self.reporter.format_phase(type(self).__name__, self.full_name)} '
               f'{"".join(uniquify_list(methods))}')

    def do_action_clean(self, action: Action):
        ''' Cleans all object paths this phase builds. '''
        for file in self.files.get_output_files():
            if file.file_type not in ['dir', 'pyke_makefile']:
                self.do_step_delete_file(action, None, file.path)

    def do_action_clean_build_directory(self, action: Action):
        ''' Wipes out the build directory. '''
        self.do_step_delete_directory(action, None, Path(self.opt_str("build_anchor")))

    def do_action_clean_external_directory(self, action: Action):
        ''' Wipes out the external package dependencies directory. '''
        self.do_step_delete_directory(action, None,
                                      Path(self.opt_str("external_repos_anchor")))
