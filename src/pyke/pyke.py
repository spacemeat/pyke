'''
Python library for building software.
'''

from enum import Enum
import importlib.util
import importlib.machinery
import os
from pathlib import Path
import subprocess
import sys
from typing import Optional
from typing_extensions import Self

from . import ansi as a
from .options import Options, OptionOp
from .utilities import InvalidOptionKey

c_success =         a.rgb_fg(0x33, 0xaf, 0x55)
c_fail =            a.rgb_fg(0xff, 0x33, 0x33)
c_phase_lt =        a.rgb_fg(0x33, 0x33, 0xff)
c_phase_dk =        a.rgb_fg(0x23, 0x23, 0x7f)
c_step_lt =         a.rgb_fg(0x33, 0xaf, 0xaf)
c_step_dk =         a.rgb_fg(0x23, 0x5f, 0x5f)
c_shell_cmd =       a.rgb_fg(0x31, 0x31, 0x32)
c_key =             a.rgb_fg(0xff, 0x8f, 0x23)
c_val_uninterp_dk = a.rgb_fg(0x5f, 0x13, 0x5f)
c_val_uninterp_lt = a.rgb_fg(0xaf, 0x23, 0xaf)
c_val_interp =      a.rgb_fg(0x33, 0x33, 0xff)

def ensure_list(o):
    '''
    Places an object in a list if it isn't already.
    '''
    return o if isinstance(o, list) else [o]

def ensure_tuple(o):
    '''
    Places an object in a tuple if it isn't already.
    '''
    return o if isinstance(o, tuple) else (o,)

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


class ReturnCode(Enum):
    ''' Encoded return code for program exit.'''
    SUCCEEDED = 0
    MAKEFILE_NOT_FOUND = 1
    MAKEFILE_DID_NOT_LOAD = 2
    INVALID_ARGS = 3
    ACTION_FAILED = 4

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
    def __init__(self, action: str, step_results: StepResult | tuple[StepResult]):
        self.action = action
        self.results = ensure_tuple(step_results)

    def __bool__(self):
        return all((bool(step) for step in self.results))


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
    def __init__(self, step_name: str, step_input: str, step_output: str,
                 cmd: Optional[str]):
        self.step_result = StepResult(step_name, step_input, step_output, cmd or '')
        report_step_start(self.step_result)

    def __enter__(self):
        return self.step_result

    def __exit__(self, *args):
        report_step_end(self.step_result)
        return False



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


_make_dir = ''





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
        self.options = Options()
        self.options |= {
            'name': 'unnamed',
            'verbosity': 0,
            'project_anchor': _make_dir,
            'gen_anchor': _make_dir,
            'use_ansi_colors': True,
            'simulate': False,
        }
        self.options |= options

        assert isinstance(options, dict)
        self.default_action = 'report'
        self.last_action_ordinal = -1
        self.last_action_result = None

        if dependencies is None:
            dependencies = []
        dependencies = ensure_list(dependencies)
        self.dependencies = []
        for dep in dependencies:
            self.set_dependency(dep)

    def push_option_overrides(self, overrides: dict):
        '''
        Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line.
        '''
        self.options |= overrides
        for dep in self.dependencies:
            dep.push_option_overrides(overrides)

    def pop_option_overrides(self, keys: list):
        '''
        Removes pushed option overrides.
        '''
        for dep in reversed(self.dependencies):
            dep.pop_option_overrides(keys)
        for key in keys:
            self.options.pop(key)

    def lopt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
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

    def sopt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
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
                action,
                StepResult('', '', '', '', ResultCode.ALREADY_UP_TO_DATE,
                f'{self.sopt("name")}.{action}'))
            return self.last_action_result

        self.last_action_ordinal = action_ordinal
        for dep in self.dependencies:
            res = dep.do(action, action_ordinal)
            if not res:
                self.last_action_result = ActionResult(
                    action,
                    StepResult('', '', '', '', ResultCode.DEPENDENCY_ERROR, dep))
                return self.last_action_result

        action_method = getattr(self, 'do_action_' + action, self.do_action_undefined)
        try:
            report_action_start(self.sopt('name'), action)
            self.last_action_result = action_method()

        except InvalidOptionKey as e:
            self.last_action_result = ActionResult(
                action,
                StepResult('', '', '', '', ResultCode.INVALID_OPTION, e))
            report_error(self.sopt('name'), action, str(e))

        report_action_end(bool(self.last_action_result))

        return self.last_action_result

    def do_action_undefined(self):
        '''
        This is the default action for actions that a phase does not support.
        Goes nowhere, does nothing.
        '''
        return ActionResult('', StepResult('', '', '', '', ResultCode.NO_ACTION))

    def do_action_report(self):
        '''
        This gives a small description of the phase.
        '''
        report = ''
        if _verbosity == 0:
            report = f'phase: {self.sopt("name")}'
        if _verbosity <= 1:
            opts_str = ''
            for k in self.options.keys():
                vu = self.options.get(k, False)
                vi = self.options.get(k)

                opts_str = ''.join((opts_str,
                                    f'{c_key}{k}: '))
                last_replace_idx = len(vu) - next(i for i, e in enumerate(reversed(vu))
                    if e[1] == OptionOp.REPLACE) - 1
                for i, vue in enumerate(vu):
                    color = c_val_uninterp_dk if i < last_replace_idx else c_val_uninterp_lt
                    indent = 0 if i == 0 else len(k) + 2
                    op = vue[1].value
                    opts_str = ''.join((opts_str,
                                        f'{" " * indent}{color}{op} {vue[0]}{a.off}\n'))

                opts_str = ''.join((opts_str,
                                    f'{" " * (len(k) + 2)}{c_val_interp}= {vi}\n'))

            report = f'{report}\n{opts_str}'
            print (report)
        return ActionResult(
            'report', StepResult('report', '', '', '', ResultCode.NO_ACTION, str(self)))


class BuildPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options, dependencies = None):
        options = {
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
            'multithreaded': 'true',
            'definitions': [],
            'additional_flags': [],
            'incremental_build': 'true',

            'build_dir': 'build',
            'build_detail': '{kind}.{toolkit}',
            'obj_dir':'int',
            'exe_dir':'bin',
            'obj_anchor': '{gen_anchor}/{build_dir}/{build_detail}/{obj_dir}',
            'exe_anchor': '{gen_anchor}/{build_dir}/{build_detail}/{exe_dir}',

            'src_dir': 'src',
            'src_anchor': '{project_anchor}/{src_dir}',
            'include_dirs': ['include'],
            'obj_basename': '', # empty means to use the basename of sources[0]
            'obj_name': '{obj_basename}.o',
            'obj_path': '{obj_anchor}/{obj_name}',
            'sources': [],

            'lib_dirs': [],
            'libs': [],
            'shared_libs': [],
            'exe_basename': 'sample',
            'exe_path': '{exe_anchor}/{exe_basename}',
        } | options
        super().__init__(options, dependencies)
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

    def get_all_src_and_object_paths(self):
        '''
        Generates (source path, object path)s for each source.
        '''
        return zip(self.get_all_src_paths(), self.get_all_object_paths())

    def get_exe_path(self):
        '''
        Makes the full exe path from options.
        '''
        return Path(self.sopt('exe_path'))

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

    def make_compile_arguments(self):
        ''' Constructs the inc_dirs portion of a gcc command.'''
        inc_dirs = self.lopt('include_dirs')
        proj_anchor = self.sopt('project_anchor')
        inc_dirs_cmd = ''.join((f'-I{proj_anchor}/{inc} ' for inc in inc_dirs))
        if len(inc_dirs_cmd) > 0:
            inc_dirs_cmd = f'{inc_dirs_cmd} '
        return {
            'inc_dirs': inc_dirs_cmd
        }

    def make_link_arguments(self):
        ''' Constructs the linking arguments of a gcc command.'''
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

        return {
            'lib_dirs': lib_dirs_cmd,
            'static_libs': static_libs_cmd,
            'shared_libs': shared_libs_cmd,
        }

    def do_step_delete_file(self, path):
        '''
        Perfoems a file deletion operation as an action step.
        '''
        step_results = None
        with ActionStep('deleting', '', str(path),
                        self.make_cmd_delete_file(path)) as step:
            step_results = step
            if path.exists():
                res, _, err = do_shell_command(step.shell_cmd)
                if res != 0:
                    step.set_result(ResultCode.COMMAND_FAILED, err)
                else:
                    step.set_result(ResultCode.SUCCEEDED)
            else:
                step.set_result(ResultCode.ALREADY_UP_TO_DATE)
        return step_results

    def do_step_create_directory(self, new_dir):
        '''
        Performs a directory creation operation as an action step.
        '''
        step_results = None
        with ActionStep('creating', '', str(new_dir),
                        f'mkdir -p {new_dir}') as step:
            step_results = step
            if not new_dir.is_dir():
                res, _, err = do_shell_command(step.shell_cmd)
                if res != 0:
                    step.set_result(ResultCode.COMMAND_FAILED, err)
                else:
                    step.set_result(ResultCode.SUCCEEDED)
            else:
                step.set_result(ResultCode.ALREADY_UP_TO_DATE)
        return step_results

    def do_step_compile_src_to_object(self, prefix, args, src_path, obj_path):
        '''
        Perform a C or C++ source compile operation as an action step.
        '''
        step_results = None
        with ActionStep('compiling', str(src_path), str(obj_path),
                        f'{prefix}-c {args["inc_dirs"]}-o {obj_path} {src_path}') as step:
            step_results = step
            if not src_path.exists():
                step.set_result(ResultCode.MISSING_INPUT, src_path)
            else:
                if not obj_path.exists() or input_is_newer(src_path, obj_path):
                    res, _, err = do_shell_command(step.shell_cmd)
                    if res != 0:
                        step.set_result(ResultCode.COMMAND_FAILED, err)
                    else:
                        step.set_result(ResultCode.SUCCEEDED)
                else:
                    step.set_result(ResultCode.ALREADY_UP_TO_DATE)
        return step_results

    def do_step_link_objects_to_exe(self, prefix, args, exe_path, object_paths):
        '''
        Perform a C or C++ source compile operation as an action step.
        '''
        object_paths_cmd = f'{" ".join((str(obj) for obj in object_paths))} '

        step_results = None
        missing_objs = []
        with ActionStep('compiling', '[*objs]', str(exe_path),
                        (f'{prefix}-o {exe_path} {object_paths_cmd}{args["lib_dirs"]}'
                         f'{args["static_libs"]}{args["shared_libs"]}')) as step:
            step_results = step
            for obj_path in object_paths:
                if not obj_path.exists():
                    missing_objs.append(obj_path)
            if len(missing_objs) > 0:
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
                        step.set_result(ResultCode.COMMAND_FAILED, err)
                    else:
                        step.set_result(ResultCode.SUCCEEDED)
                else:
                    step.set_result(ResultCode.ALREADY_UP_TO_DATE)
        return step_results

    def do_step_compile_srcs_to_exe(self, prefix, args, src_paths, exe_path):
        '''
        Perform a multiple C or C++ source compile to executable operation as an action step.
        '''
        src_paths_cmd = f'{" ".join((str(src) for src in src_paths))} '

        step_results = None
        missing_srcs = []
        with ActionStep('compiling', '[*srcs]', str(exe_path),
                        f'{prefix} {args["inc_dirs"]}-o {exe_path} '
                        f'{src_paths_cmd}{args["lib_dirs"]}'
                        f'{args["static_libs"]}{args["shared_libs"]}') as step:
            step_results = step
            for src_path in src_paths:
                if not src_path.exists():
                    missing_srcs.append(src_path)
            if len(missing_srcs) > 0:
                step.set_result(ResultCode.MISSING_INPUT, missing_srcs)
            else:
                exe_exists = exe_path.exists()
                must_build = not exe_exists
                for src_path in src_paths:
                    if not exe_exists or input_is_newer(src_path, exe_path):
                        must_build = True
                if must_build:
                    res, _, err = do_shell_command(step.shell_cmd)
                    if res != 0:
                        step.set_result(ResultCode.COMMAND_FAILED, err)
                    else:
                        step.set_result(ResultCode.SUCCEEDED)
                else:
                    step.set_result(ResultCode.ALREADY_UP_TO_DATE)
        return step_results


class CompilePhase(BuildPhase):
    '''
    Phase class for building C/C++ files to objects.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'build_operation': 'compile_to_object',
        } | options
        super().__init__(options, dependencies)
        self.default_action = 'build'

    def do_action_clean(self):
        '''
        Cleans all object paths this phase builds.
        '''
        step_results = []
        for _, obj_path in self.get_all_src_and_object_paths():
            step_results.append(self.do_step_delete_file(obj_path))

        return ActionResult('clean', tuple(step_results))

    def do_action_build(self):
        '''
        Builds all object paths.
        '''
        step_results = []
        prefix = self.make_build_command_prefix()
        args = self.make_compile_arguments()

        for src_path, obj_path in self.get_all_src_and_object_paths():
            step_results.append(self.do_step_create_directory(obj_path.parent))

            if bool(step_results[-1]):
                step_results.append(self.do_step_compile_src_to_object(
                    prefix, args, src_path, obj_path))

        return ActionResult('build', tuple(step_results))


class LinkPhase(BuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'build_operation': 'link_to_executable',
        } | options
        super().__init__(options, dependencies)

    def get_all_object_paths(self):
        '''
        Gets the object file paths from each dependency.
        '''
        for dep in self.dependencies:
            for obj_path in dep.get_all_object_paths():
                yield obj_path

    def do_action_clean(self):
        '''
        Cleans all object paths this phase builds.
        '''
        exe_path = self.get_exe_path()

        step_results = []
        step_results.append(self.do_step_delete_file(exe_path))
        return ActionResult('clean', tuple(step_results))

    def do_action_build(self):
        '''
        Builds all object paths.
        '''

        step_results = []

        object_paths = self.get_all_object_paths()
        exe_path = self.get_exe_path()

        prefix = self.make_build_command_prefix()
        args = self.make_link_arguments()

        step_results.append(self.do_step_create_directory(exe_path.parent))
        if bool(step_results[-1]):
            step_results.append(self.do_step_link_objects_to_exe(
                prefix, args, exe_path, object_paths))

        return ActionResult('build', tuple(step_results))


class CompileAndLinkPhase(BuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'build_operation': 'compile_to_executable',
        } | options
        super().__init__(options, dependencies)

    def do_action_clean(self):
        '''
        Cleans all object paths this phase builds.
        '''
        exe_path = self.get_exe_path()

        step_results = []

        if self.sopt('incremental_build') != 'false':
            for _, obj_path in self.get_all_src_and_object_paths():
                step_results.append(self.do_step_delete_file(obj_path))

        step_results.append(self.do_step_delete_file(exe_path))

        return ActionResult('clean', tuple(step_results))

    def do_action_build(self):
        '''
        Builds all object paths.
        '''
        step_results = []
        exe_path = self.get_exe_path()

        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()
        l_args = self.make_link_arguments()

        if self.sopt('incremental_build') != 'false':
            for src_path, obj_path in self.get_all_src_and_object_paths():
                step_results.append(self.do_step_create_directory(obj_path.parent))

                if bool(step_results[-1]):
                    step_results.append(self.do_step_compile_src_to_object(
                        prefix, c_args, src_path, obj_path))

            if all((bool(res) for res in step_results)):
                object_paths = self.get_all_object_paths()

                step_results.append(self.do_step_create_directory(exe_path.parent))
                if bool(step_results[-1]):
                    step_results.append(self.do_step_link_objects_to_exe(
                        prefix, l_args, exe_path, object_paths))
        else:
            src_paths = self.get_all_src_paths()

            step_results.append(self.do_step_create_directory(exe_path.parent))
            if bool(step_results[-1]):
                step_results.append(self.do_step_compile_srcs_to_exe(
                    prefix, c_args | l_args, src_paths, exe_path))

        return ActionResult('build', tuple(step_results))


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
    global _make_dir

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

    _make_dir = str(make_path.parent)
    run_make_file(make_path, cache_make)

    active_phase = _using_phases[-1]
    phase_map = {phase.sopt('name'): phase for phase in _using_phases}

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
                k, v = override.split(':')
                active_phase.push_option_overrides({k: v})
            else:
                active_phase.pop_option_overrides([override])

        else:
            action = arg
            if not active_phase.do(action):
                return ReturnCode.ACTION_FAILED.value

        idx += 1

    return ReturnCode.SUCCEEDED.value

if __name__ == '__main__':
    main()
