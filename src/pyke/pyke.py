'''
Python library for building software.
'''

from enum import Enum
import importlib.util
import importlib.machinery
import os
import re
from pathlib import Path
import subprocess
import sys
from typing import Optional
from typing_extensions import Self

from . import ansi as a

c_success =       a.rgb_fg(0x33, 0xaf, 0x55)
c_fail =          a.rgb_fg(0xff, 0x33, 0x33)
c_phase_lt =      a.rgb_fg(0x33, 0x33, 0xff)
c_phase_dk =      a.rgb_fg(0x23, 0x23, 0x7f)
c_step_lt =       a.rgb_fg(0x33, 0xaf, 0xaf)
c_step_dk =       a.rgb_fg(0x23, 0x5f, 0x5f)
c_shell_cmd =     a.rgb_fg(0x31, 0x31, 0x32)

def ensure_list(o):
    '''
    Places an object in a list if it isn't already.
    '''
    return o if isinstance(o, list) else [o]

def ensure_tuple(o):
    '''
    Places an object in a tuple if it isn't already.
    '''
    return o if isinstance(0, tuple) else (o)

def lget(l, idx, default=None):
    '''
    Safe one-liner for defaulting a value on an out-of-range list index.
    '''
    try:
        return l[idx]
    except IndexError:
        return default


class PhaseNotFoundError(Exception):
    '''
    Raised when referencing a phase by name which does not match any existing phase.
    '''

class InvalidOptionOverrideError(Exception):
    '''
    Raised when referencing an option which was not given a default.
    '''

class UnsupportedToolkitError(Exception):
    '''
    Raised when a toolkit is specified that is not supported.
    '''

class UnsupportedLanguageError(Exception):
    '''
    Raised when a language is specified that is not supported.
    '''

class CircularDependencyError(Exception):
    '''
    Raised when a circular phase dependency is attempted.
    '''

class InvalidOptionKey(Exception):
    '''
    Raised when an option is referenced which is not allowed for this phase.
    '''

class ResultCode(Enum):
    '''
    Encoded result of one step of an action. Values >= 0 are success codes.
    '''
    NO_ACTION = 0
    SUCCEEDED = 1
    ALREADY_UP_TO_DATE = 2
    MISSING_INPUT = -1
    COMMAND_FAILED = -2
    DEPENDENCY_ERROR = -3
    INVALID_OPTION = -4


_verbosity = 1

class StepResult:
    '''
    Result of one step of an action.
    '''
    def __init__(self, step_name: str, step_input: str, step_output: str, shell_cmd: str,
                 code: ResultCode = ResultCode.NO_ACTION, info = None):
        self.step_name = step_name
        self.step_input = step_input
        self.step_output = step_output
        self.shell_cmd = shell_cmd
        self.code = code
        self.info = info

    def set_result(self, code = ResultCode.NO_ACTION, info = None):
        ''' Sets the step results to this object. '''
        self.code = code
        self.info = info

    def __bool__(self):
        return self.code.value >= 0

    def did_succeed(self):
        '''
        Quick ask if a step was successful.
        '''
        return bool(self)


class ActionResult:
    '''
    Result of an action.
    '''
    def __init__(self, action: str, did_succeed: bool,
                 step_results: StepResult | tuple[StepResult]):
        self.action = action
        self.did_succeed = did_succeed
        self.results = ensure_tuple(step_results)

    def __bool__(self):
        return self.did_succeed

def report_phase(phase: str, action: str):
    '''
    Prints a phase summary.
    '''
    print (f'{c_phase_lt}{action}{c_phase_dk} - phase: {c_phase_lt}'
           f'{phase}{c_phase_dk}:{a.off}')

def report_error(phase: str, action: str, err: str):
    '''
    Print an error string to the console in nice, bright red.
    '''
    report_phase(phase, action)
    print (f'{err}')

def report_action_start(phase: str, action: str):
    ''' Reports on the start of an action. '''
    if _verbosity > 0:
        report_phase(phase, action)

def report_action_end(success: bool):
    ''' Reports on the start of an action. '''
    if _verbosity > 1 and success:
        print (f'{c_phase_dk} ... {c_success}succeeded{a.off}')
    elif _verbosity > 0 and not success:
        print (f'{c_phase_dk} ... {c_fail}failed{a.off}')

def report_step_start(result: StepResult):
    ''' Reports on the start of an action step. '''
    if _verbosity > 0:
        print (f'{c_step_dk}{result.step_name} {c_step_lt}{result.step_input}'
               f'{c_step_dk} -> {c_step_lt}{result.step_output}{a.off}', end='')
    if _verbosity > 1:
        print (f'\n{c_shell_cmd}{result.shell_cmd}{a.off}', end='')

def report_step_end(result: StepResult):
    ''' Reports on the end of an action step. '''
    if result.code.value >= 0:
        if _verbosity > 0:
            print (f'{c_step_dk} ({c_success}{result.code.name}{c_step_dk}){a.off}')
    elif result.code.value < 0:
        if _verbosity > 0:
            print (f'{c_step_dk} ({c_fail}{result.code.name}{c_step_dk}){a.off}')
        print (f'{result.info}', file=sys.stderr)


class ActionStep:
    ''' Manages the creation of a StepResult using the "with" syntax. '''
    def __init__(self, results_list, step_name: str, step_input: str, step_output: str,
                 cmd: Optional[str]):
        self.results_list = results_list
        self.step_result = StepResult(step_name, step_input, step_output, cmd or '')
        report_step_start(self.step_result)

    def __enter__(self):
        return self.step_result

    def __exit__(self, *args):
        self.results_list.append(self.step_result)
        report_step_end(self.step_result)
        return False


re_interp_option = re.compile(r'{([a-zA-Z0-9_]+?)}')

def input_is_newer(in_path: Path, out_path: Path):
    '''
    Compares the modified times of two files.
    '''
    if not in_path.exists():
        raise ValueError(f'Input file "{in_path}" does not exist; cannot compare m-times.')

    outm = out_path.stat().st_mtime if out_path.exists() else 0
    inm = in_path.stat().st_mtime
    return inm > outm

def do_shell_command(cmd):
    '''
    Reports, and then performs the given shell command as a subprocess. It is run in its
    own shell instance, each with its own environment.
    '''
    res = subprocess.run(cmd, shell=True, capture_output=True, encoding='utf-8', check = False)
    return (res.returncode, res.stdout, res.stderr)


_pyke_dir = ''

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
    def __init__(self, options: dict, dependencies: Self | list[Self] | None = None):
        if dependencies is None:
            dependencies = []
        dependencies = ensure_list(dependencies)

        self.defaults = {
            'name': 'unnamed',
            'verbosity': '0',
            'project_anchor': _pyke_dir,
            'gen_anchor': _pyke_dir,
        }
        assert isinstance(options, dict)
        self.options = options
        self.option_overrides = []
        self.default_action = 'terse_report'
        self.last_action_ordinal = -1
        self.last_action_result = None
        self.dependencies = []
        for dep in dependencies:
            self.set_dependency(dep)

    def push_option_overrides(self, overrides: dict):
        '''
        Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line.
        '''
        self.option_overrides.append(overrides)
        for dep in self.dependencies:
            dep.push_option_overrides(overrides)

    def pop_option_overrides(self, keys: list):
        '''
        Removes pushed option overrides.
        '''
        for dep in reversed(self.dependencies):
            dep.pop_option_overrides(keys)
        for key in keys:
            for overrides in reversed(self.option_overrides):
                if key in overrides:
                    del overrides[key]

    def _interp_str(self, fstring: str, overrides: dict | None = None):
        val = fstring
        while re_interp_option.search(val, 0):
            val = re_interp_option.sub(lambda m: str(self.sopt(m.group(1), overrides)), val)
        return val

    def lopt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        '''
        default = self.defaults.get(key, None)
        if default is None:
            print (self.defaults)
            raise InvalidOptionKey(f'Invalid option "{key}".')
        if not isinstance(default, list):
            raise InvalidOptionKey(f'Option "{key}" is not in list form.')

        if overrides is None:
            overrides = {}

        opts_with_overrides = self.options.copy()
        opts_with_overrides |= dict((k, v) for d in self.option_overrides for k, v, in d.items())
        opts_with_overrides |= overrides
        val = ensure_list(opts_with_overrides.get(key, default))
        if interpolate:
            return [self._interp_str(v, overrides) for v in val]
        return val

    def sopt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        '''
        default = self.defaults.get(key, None)
        if default is None:
            raise InvalidOptionKey(f'Invalid option "{key}".')
        if not isinstance(default, str):
            raise InvalidOptionKey(f'Option "{key}" is not in string form.')

        if overrides is None:
            overrides = {}

        opts_with_overrides = self.options.copy()
        opts_with_overrides |= dict((k, v) for d in self.option_overrides for k, v, in d.items())
        opts_with_overrides |= overrides

        val = str(opts_with_overrides.get(key, default))
        if interpolate:
            return self._interp_str(val, overrides)
        return val

    def __str__(self):
        return self.sopt("name")

    def __repr__(self):
        return self.sopt("name")

    def clone(self, options: dict | None = None):
        '''
        Returns a clone of this instance. The clone has the same
        options (also copied) but its own dependencies and action
        results state.
        '''
        if options is None:
            options = {}

        return type(self)({**self.options.copy(), **options})

    def is_in_dependency_tree(self, dep_to_find: Self):
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
            if new_dep.is_in_dependency_tree(self) is not None:
                raise CircularDependencyError(
                    f'Attempt to set a circular dependency {str(new_dep)} '
                    f'to phase {str(self)}. Not cool.')
            self.dependencies.append(new_dep)

    def _get_action_ordinal(self, action_ordinal: int):
        '''
        Replaces the default action_ordinal with the proper internal tracking
        ordinal.
        '''
        if action_ordinal == -1:
            return self.last_action_ordinal + 1
        return action_ordinal

    def make_cmd_delete_file(self, path: Path):
        '''
        Returns an appropriate command for deleting a file.
        '''
        return f'rm {str(path)}'

    def do(self, action: str, action_ordinal: int = -1) -> ActionResult:
        '''
        Performs an action, such as 'build' or 'run'. 

        First, each dependency phase is called with the same action, depth-first.
        Next, the corresponding 'do_action_<action>' method is called for this
        phase.

        Each invoked action is bound to an action_ordinal, an integer which 
        specifies a particular action which is tracked to prevent repeat actions
        for phases which are dependents of multiple other phases. This is managed
        internally.
        '''

        # set this on every do(), so each phase still controls its own verbosity
        global _verbosity
        _verbosity = int(self.sopt('verbosity'))

        action_ordinal = self._get_action_ordinal(action_ordinal)
        if self.last_action_ordinal == action_ordinal:
            self.last_action_result = ActionResult(
                action, True,
                StepResult('', '', '', '', ResultCode.ALREADY_UP_TO_DATE,
                f'{self.sopt("name")}.{action}'))
            return self.last_action_result

        self.last_action_ordinal = action_ordinal
        for dep in self.dependencies:
            res = dep.do(action, action_ordinal)
            if not res:
                self.last_action_result = ActionResult(
                    action, False,
                    StepResult('', '', '', '', ResultCode.DEPENDENCY_ERROR, dep))
                return self.last_action_result

        action_method = getattr(self, 'do_action_' + action, self.do_action_undefined)
        try:
            report_action_start(self.sopt('name'), action)
            self.last_action_result = action_method()

        except InvalidOptionKey as e:
            self.last_action_result = ActionResult(
                action, False,
                StepResult('', '', '', '', ResultCode.INVALID_OPTION, e))
            report_error(self.sopt('name'), action, str(e))

        is_success = False
        if isinstance(self.last_action_result, ActionResult):
            is_success = self.last_action_result.did_succeed
        report_action_end(is_success)

        return self.last_action_result

    def do_action_undefined(self):
        '''
        This is the default action for actions that a phase does not support.
        Goes nowhere, does nothing.
        '''
        return ActionResult('', True, StepResult('', '', '', '', ResultCode.NO_ACTION))

    def do_action_terse_report(self):
        '''
        This gives a small description of the phase.
        '''
        return ActionResult('terse_report', True,
                            StepResult('report', '', '', '', ResultCode.NO_ACTION, str(self)))

    def do_action_verbose_report(self):
        '''
        This gives a more detailed description of the phase.
        '''
        return ActionResult('verbose_report', True,
                            StepResult('report', '', '', '', ResultCode.NO_ACTION,
                                       f'{self} deps: {(dep for dep in self.dependencies)}'))

    def do_action_debug_report(self):
        '''
        This gives a debug view of the phase.
        '''
        return ActionResult('debug_report', True,
                            StepResult('report', '', '', '', ResultCode.NO_ACTION,
                                       f'{repr(self)} deps: '
                                       f'{(str(dep) for dep in self.dependencies)}'))


class BuildPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options, dependencies = None):
        super().__init__(options, dependencies)
        self.defaults |= {
            'toolkit': 'gnu',
            'language': 'c++',
            'language_version': '23',
            'warnings': ['all', 'extra', 'error'],
            'kind': 'release',
            'debug_debug_level': '2',
            'debug_optimization': '0',
            'debug_flags': ['-fno-inline', '-fno-lto', '-DDEBUG'],
            'release_debug_level': '0',
            'release_optimization': '2',
            'release_flags': ['-DNDEBUG'],
            'kind_debug_level': '{{kind}_debug_level}',
            'kind_optimization': '{{kind}_optimization}',
            'kind_flags': '{{kind}_flags}',
            'packages': [],
            'multithreaded': 'True',
            'definitions': [],
            'additional_flags': [],
            'build_dir': 'build',
            'build_detail': '{kind}.{toolkit}',
            'obj_dir':'int',
            'exe_dir':'bin',
            'obj_anchor': '{gen_anchor}/{build_dir}/{build_detail}/{obj_dir}',
            'exe_anchor': '{gen_anchor}/{build_dir}/{build_detail}/{exe_dir}',
        }
        self.default_action = 'build'

    def make_build_command_prefix(self):
        '''
        Makes a partial build command line that several build phases can further augment and use.
        '''
        toolkit = self.sopt('toolkit')
        if toolkit == 'gnu':
            return self._make_build_command_prefix_gnu()
        if toolkit == 'clang':
            return self._make_build_command_prefix_clang()
        if toolkit == 'visual_studio':
            return self._make_build_command_vs()
        raise UnsupportedToolkitError(f'Specified toolkit "{toolkit}" is not supported.')

    def _make_build_command_prefix_gnu(self):
        lang = str(self.sopt('language')).lower()
        ver = str(self.sopt('language_version')).lower()
        prefix = ''
        if lang == 'c++':
            prefix = f'g++ -std=c++{ver} '
        elif lang == 'c':
            prefix = f'gcc -std=c{ver} '
        else:
            raise UnsupportedLanguageError(f'Specified language "{lang}" is not supported.')
        return self._make_build_command_prefix_gnu_clang(prefix)

    def _make_build_command_prefix_clang(self):
        lang = str(self.sopt('language')).lower()
        ver = str(self.sopt('language_version')).lower()
        prefix = ''
        if lang == 'c++':
            prefix = f'clang++ -std=c++{ver} '
        elif lang == 'c':
            prefix = f'clang -std=c{ver} '
        else:
            raise UnsupportedLanguageError(f'Specified language "{lang}" is not supported.')
        return self._make_build_command_prefix_gnu_clang(prefix)

    def _make_build_command_prefix_gnu_clang(self, prefix):
        compile_only = self.sopt('build_operation') == 'build_obj'
        c = '-c ' if compile_only else ''

        warn = ''.join((f'-W{w} ' for w in self.lopt('warnings')))

        g = f'-g{self.sopt("kind_debug_level")} '
        o = f'-O{self.sopt("kind_optimization")} '

        defs = ''.join((f'-D{d} ' for d in self.lopt('definitions')))

        additional_flags = ''.join((str(flag) for flag in self.lopt('additional_flags')))

        build_string = f'{prefix}{warn}{c}{g}{o}{defs}{additional_flags} '
        return build_string

    def _make_build_command_vs(self):
        pass


class CompilePhase(BuildPhase):
    '''
    Phase class for building C/C++ files to objects.
    '''
    def __init__(self, options, dependencies = None):
        super().__init__(options, dependencies)
        self.defaults |= {
            'build_operation': 'compile_to_object',
            'src_dir': 'src',
            'src_anchor': '{project_anchor}/{src_dir}',
            'include_dirs': [],
            'obj_basename': '', # empty means to use the basename of sources[0]
            'obj_name': '{obj_basename}.o',
            'obj_path': '{obj_anchor}/{obj_name}',
            'sources': []
        }
        self.default_action = 'build'

    def get_source(self, src_idx):
        '''
        Gets the src_idxth source from options. Ensures the result is a Path.
        '''
        sources = self.lopt('sources')
        return sources[src_idx]

    def make_src_path(self, src_idx):
        '''
        Makes a full source path out of the src_idxth source from options.
        '''
        src = self.get_source(src_idx)
        return Path(f"{self.sopt('src_anchor')}/{src}")

    def make_obj_path_from_src(self, src_idx):
        '''
        Makes the full object path from a single source by index.
        '''
        src = self.get_source(src_idx)
        basename = Path(src).stem
        return Path(self.sopt('obj_path', {'obj_basename': basename}))

    def get_all_src_paths(self):
        '''
        Generate te full path for each source file.
        '''
        sources = self.lopt('sources')
        for i in range(len(sources)):
            yield self.make_src_path(i)

    def get_all_object_paths(self):
        '''
        Generate the full path for each target object file.
        '''
        sources = self.lopt('sources')
        for i in range(len(sources)):
            yield self.make_obj_path_from_src(i)

    def get_all_src_object_paths(self):
        '''
        Generates (source path, object path)s for each source.
        '''
        return zip(self.get_all_src_paths(), self.get_all_object_paths())

    def do_action_clean(self):
        '''
        Cleans all object paths this phase builds.
        '''
        is_action_success = True
        step_results = []

        for _, obj_path in self.get_all_src_object_paths():
            with ActionStep(step_results, 'deleting', '', str(obj_path),
                            self.make_cmd_delete_file(obj_path)) as step:
                if obj_path.exists():
                    res, _, err = do_shell_command(step.shell_cmd)
                    if res != 0:
                        is_action_success = False
                        step.set_result(ResultCode.COMMAND_FAILED, err)
                    else:
                        step.set_result(ResultCode.SUCCEEDED)
                else:
                    step.set_result(ResultCode.ALREADY_UP_TO_DATE)

        return ActionResult('clean', is_action_success, tuple(step_results))

    def do_action_build(self):
        '''
        Builds all object paths.
        '''
        is_action_success = True
        step_results = []

        prefix = self.make_build_command_prefix()

        inc_dirs = self.lopt('include_dirs')
        proj_anchor = self.sopt('project_anchor')
        inc_dirs_cmd = ''.join((f'-I{proj_anchor}/{inc} ' for inc in inc_dirs))
        if len(inc_dirs_cmd) > 0:
            inc_dirs_cmd = f'{inc_dirs_cmd} '

        for src_path, obj_path in self.get_all_src_object_paths():
            is_step_success = True
            with ActionStep(step_results, 'creating', '', str(obj_path.parent),
                            f'mkdir -p {obj_path.parent}') as step:
                if not obj_path.parent.is_dir():
                    res, _, err = do_shell_command(step.shell_cmd)
                    if res != 0:
                        is_step_success = False
                        step.set_result(ResultCode.COMMAND_FAILED, err)
                    else:
                        step.set_result(ResultCode.SUCCEEDED)
                else:
                    step.set_result(ResultCode.ALREADY_UP_TO_DATE)

            if is_step_success:
                with ActionStep(step_results, 'compiling', str(src_path), str(obj_path),
                                f'{prefix}-c {inc_dirs_cmd}-o {obj_path} {src_path}') as step:
                    if not src_path.exists():
                        is_step_success = False
                        step.set_result(ResultCode.MISSING_INPUT, src_path)
                    else:
                        if not obj_path.exists() or input_is_newer(src_path, obj_path):
                            res, _, err = do_shell_command(step.shell_cmd)
                            if res != 0:
                                is_step_success = False
                                step.set_result(ResultCode.COMMAND_FAILED, err)
                            else:
                                step.set_result(ResultCode.SUCCEEDED)
                        else:
                            step.set_result(ResultCode.ALREADY_UP_TO_DATE)

            is_action_success = is_action_success and is_step_success

        return ActionResult('build', is_action_success, tuple(step_results))


class LinkPhase(BuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options, dependencies = None):
        super().__init__(options, dependencies)
        self.defaults |= {
            'build_operation': 'link_to_executable',
            'lib_dirs': [],
            'libs': [],
            'shared_libs': [],
            'exe_name': 'sample',
            'exe_path': '{exe_anchor}/{exe_name}',
        }

    def get_object_paths(self):
        '''
        Gets the object file paths from each dependency.
        '''
        obj_paths = []
        for dep in self.dependencies:
            obj_paths.extend(dep.get_all_object_paths())
        return obj_paths

    def make_exe_path(self):
        '''
        Makes the full exe path from options.
        '''
        return Path(self.sopt('exe_path'))

    def do_action_clean(self):
        '''
        Cleans all object paths this phase builds.
        '''
        exe_path = self.make_exe_path()

        is_action_success = True
        step_results = []

        with ActionStep(step_results, 'deleting', '', str(exe_path),
                        self.make_cmd_delete_file(exe_path)) as step:
            if exe_path.exists():
                res, _, err = do_shell_command(step.shell_cmd)
                if res != 0:
                    is_action_success = False
                    step.set_result(ResultCode.COMMAND_FAILED, err)
                else:
                    step.set_result(ResultCode.SUCCEEDED)
            else:
                step.set_result(ResultCode.ALREADY_UP_TO_DATE)

        return ActionResult('clean', is_action_success, tuple(step_results))

    def do_action_build(self):
        '''
        Builds all object paths.
        '''
        is_action_success = True
        step_results = []

        prefix = self.make_build_command_prefix()

        object_paths = self.get_object_paths()
        exe_path = self.make_exe_path()

        object_paths_cmd = f'{" ".join((str(obj) for obj in object_paths))} '

        lib_dirs = self.lopt('lib_dirs')
        lib_dirs_cmd = ''.join((f'-L{lib_dir} ' for lib_dir in lib_dirs))

        static_libs = self.lopt('libs')
        static_libs_cmd = ''.join((f'-l{lib} ' for lib in static_libs))
        if len(static_libs_cmd) > 0:
            static_libs_cmd = f'-Wl,-Bstatic {static_libs_cmd}'

        # TODO: Ensure this is all kinda correct. I'm learning about rpath/$ORIGIN.
        shared_libs = self.lopt('shared_libs')
        shared_libs_cmd = ''.join((f'-l{so} ' for so in shared_libs))
        if len(shared_libs_cmd) > 0:
            shared_libs_cmd = f'-Wl,-Bdynamic {shared_libs_cmd} -Wl,-rpath,$ORIGIN -Wl,-z,origin'

        with ActionStep(step_results, 'creating', '', str(exe_path.parent),
                        f'mkdir -p {exe_path.parent}') as step:
            if not exe_path.parent.is_dir():
                res, _, err = do_shell_command(step.shell_cmd)
                if res != 0:
                    is_action_success = False
                    step.set_result(ResultCode.COMMAND_FAILED, err)
                else:
                    step.set_result(ResultCode.SUCCEEDED)
            else:
                step.set_result(ResultCode.ALREADY_UP_TO_DATE)

        missing_objs = []
        if is_action_success:
            with ActionStep(step_results, 'linking', '[*src]', str(exe_path),
                            (f'{prefix}-o {exe_path} {object_paths_cmd}{lib_dirs_cmd}'
                             f'{static_libs_cmd}{shared_libs_cmd}')) as step:
                for obj_path in object_paths:
                    if not obj_path.exists():
                        missing_objs.append(obj_path)
                if len(missing_objs) > 0:
                    is_action_success = False
                    step.set_result(ResultCode.MISSING_INPUT, missing_objs)
                else:
                    exe_exists = exe_path.exists()
                    must_build = not exe_exists
                    for obj_path in object_paths:
                        if not exe_exists or input_is_newer(obj_path, exe_path):
                            must_build = True
                    if must_build:
                        res, _, err = do_shell_command(step.shell_cmd)
                        if res != 0:
                            is_action_success = False
                            step.set_result(ResultCode.COMMAND_FAILED, err)
                        else:
                            step.set_result(ResultCode.SUCCEEDED)
                    else:
                        step.set_result(ResultCode.ALREADY_UP_TO_DATE)

        return ActionResult('build', is_action_success, tuple(step_results))


_using_phases = []

def use_phases(phases: Phase | list[Phase] | tuple[Phase]):
    '''
    Called by the user's pyke program to register phases for use in the project.
    '''
    if isinstance(phases, Phase):
        phases = [phases]
    else:
        phases = list(phases)
    _using_phases.extend(phases)


def run_pyke_file(pyke_path):
    if pyke_path.exists:
        spec = importlib.util.spec_from_file_location('pyke', pyke_path)
        if spec:
            module = importlib.util.module_from_spec(spec)
            loader = spec.loader
            if loader:
                loader.exec_module(module)
                return

        print (f'"{pyke_path}" could not be loaded.')
        sys.exit(2)

    else:
        print (f'"{pyke_path}" was not found.')
        sys.exit(1)


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
    -m, --module: Specifies the module (pyke file) to be run. Must precede any arguments that
        are not -v of -h. Actions are performed relative to the module's directory, unless an
        option override (-o anchor:[dir]) is given, in which case they are performed relative to
        the given working directory. Immediately after running the module, the active phase
        is selected as the last phase added to use_phase()/use_phases(). This can be overridden
        by -p.
        If no -m argument is given, pyke will look for and run ./pyke.py.
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

    Looks for ./pyke.py && loads the last phase in _using_phases && runs the default action.
    $ pyke
    $ pyke -m .

    Looks for ./simple_test.py && loads the last phase in _using_phases && runs the default action.
    $ pyke -m ./simple_test.py

    Looks for ../../pyke.py && loads the last phase in _using_phases && runs the default
    action from the current directory. This will emplace build targets relative to ../../.
    $ pyke -m ../../

    Looks for ../../pyke.py && loads the last phase in _using_phases && runs the default
    action from the current directory. This will emplace build targets relative to ./.
    $ pyke -m../../ -o anchor:$PWD

    Looks for ./pyke.py && loads && runs the default action, overriding the options in the loaded
    phase and all dependent phases.
    $ pyke -o kind:debug -o verbosity:0

    Looks for ./pyke.py && loads the phase named "alt_project" && runs its default action.
    $ pyke -p alt_project

    Looks for ./pyke.py && loads the last phase && runs the action named "build"
    $ pyke build

    Looks for ./pyke.py && loads && overrides the "time_run" option && runs the "clean", "build", 
    and "run" actions successively, given the success of each previous action.
    $ pyke -o time_run:true clean build run

    Looks for ./pyke.py && loads && runs the "clean" and "build" actions && then overrides the
    "time_run" option and runs the "run" action.
    $ pyke clean build -otime_run:true run
    ''')

def main():
    current_dir = os.getcwd()
    pyke_file = 'pyke.py'
    global _pyke_dir

    idx = 1
    arg = sys.argv[idx]

    if arg in ['-v', '--version']:
        print_version()
        return 0
    if arg in ['-h', '--help']:
        print_help()
        return 0

    if arg.startswith('-m') or arg == '--module':
        pyke_file = ''
        if len(arg) > 2:
            pyke_file = sys.argv[idx][2:]
        else:
            idx += 1
            pyke_file = sys.argv[idx]

    pyke_path = Path(current_dir) / pyke_file
    if not pyke_file.endswith('.py'):
        pyke_path = pyke_path / 'pyke.py'

    _pyke_dir = str(pyke_path.parent)
    run_pyke_file(pyke_path)

    active_phase = _using_phases[-1]
    phase_map = {phase.sopt('name'): phase for phase in _using_phases}

    idx += 1
    while idx < len(sys.argv):
        arg = sys.argv[idx]

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
            k, v = override.split(':')
            if v:
                active_phase.push_option_overrides({k: v})
            else:
                active_phase.pop_option_override([k])

        else:
            action = arg
            if not active_phase.do(action):
                return 255

        idx += 1

    return 0

if __name__ == '__main__':
    main()
