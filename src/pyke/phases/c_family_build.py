''' Contains the BuildPhase intermediate phase class. '''

from functools import partial
import os
from pathlib import Path
from typing import TypeAlias

from ..action import Action, Step, Result, ResultCode
from ..utilities import (UnsupportedToolkitError, UnsupportedLanguageError,
                         input_path_is_newer, do_shell_command)
from .phase import Phase

Steps: TypeAlias = list[Step] | Step | None


class CFamilyBuildPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = {
            'toolkit': 'gnu',
            'language': 'c++',
            'language_version': '23',
            'kind': 'release',
            'target_os_gnu': 'posix',
            'target_os_clang': 'posix',
            'target_os_visualstudio': 'windows',
            'tool_args_gnu': 'gnuclang',
            'tool_args_clang': 'gnuclang',
            'tool_args_visualstudio': 'visualstudio',
            'gnuclang_warnings': ['all', 'extra', 'error'],
            'gnuclang_debug_debug_level': '2',
            'gnuclang_debug_optimization': 'g',
            'gnuclang_debug_flags': ['-fno-inline', '-fno-lto', '-DDEBUG'],
            'gnuclang_release_debug_level': '0',
            'gnuclang_release_optimization': '2',
            'gnuclang_release_flags': ['-DNDEBUG'],
            'visualstudio_warnings': [],
            'visualstudio_debug_debug_level': '',
            'visualstudio_debug_optimization': '',
            'visualstudio_debug_flags': [],
            'visualstudio_release_debug_level': '',
            'visualstudio_release_optimization': '',
            'visualstudio_release_flags': [],
            'debug_level': '{{tool_args_{toolkit}}_{kind}_debug_level}',
            'optimization': '{{tool_args_{toolkit}}_{kind}_optimization}',
            'kind_flags': '{{tool_args_{toolkit}}_{kind}_flags}',
            'warnings': '{{tool_args_{toolkit}}_warnings}',
            'pkg_config': [],
            'posix_threads': False,
            'definitions': [],
            'additional_flags': [],
            'incremental_build': True,

            'thin_archive': False,
            'relocatable': False,
            'export_dynamic': False,

            'inc_dir': '.',
            'include_anchor': '{static_anchor}/{inc_dir}',
            'include_dirs': ['include'],

            'src_dir': 'src',
            'src_anchor': '{static_anchor}/{src_dir}',
            'sources': [],

            'prebuilt_obj_dir': 'prebuilt_obj',
            'prebuilt_obj_anchor': '{static_anchor}/{prebuilt_obj_dir}',
            'prebuilt_objs': [],

            'target_path': '',
            'build_for_deployment': True,
            'generate_versioned_sonames': True,

            'build_dir': 'build',
            'build_detail': '{kind}.{toolkit}',
            'build_anchor': '{gen_anchor}/{build_dir}',
            'build_detail_anchor': '{build_anchor}/{build_detail}',

            'obj_dir': 'int',
            'obj_basename': '',
            'posix_obj_file': '{obj_basename}.o',
            'windows_obj_file': '{obj_basename}.obj',
            'obj_file': '{{target_os_{toolkit}}_obj_file}',
            'obj_anchor': '{build_detail_anchor}/{obj_dir}',
            'obj_path': '{obj_anchor}/{obj_file}',

            'archive_dir':'lib',
            'archive_basename': '{name}',
            'posix_archive_file': 'lib{archive_basename}.a',
            'windows_archive_file': '{archive_basename}.lib',
            'archive_file': '{{target_os_{toolkit}}_archive_file}',
            'archive_anchor': '{build_detail_anchor}/{archive_dir}',
            'archive_path': '{archive_anchor}/{archive_file}',

            'rpath': {},   # {dir: str, uses_ORIGIN: bool}
            'position_independent_code': False,
            # TODO: 'symbol_visibility': 'hidden', # see https://gcc.gnu.org/wiki/Visibility

            'shared_object_dir': 'bin',
            'shared_object_basename': '{name}',
            'so_major': 1,
            'so_minor': 0,
            'so_patch': 0,
            'posix_so_linker_name': 'lib{shared_object_basename}.so',
            'posix_so_soname': '{posix_so_linker_name}.{so_major}',
            'posix_so_real_name': '{posix_so_soname}.{so_minor}.{so_patch}',
            'posix_shared_object_file': '{posix_so_real_name}',
            'windows_shared_object_file': '{shared_object_basename}.dll',
            'shared_object_file': '{{target_os_{toolkit}}_shared_object_file}',
            'shared_object_anchor': '{build_detail_anchor}/{shared_object_dir}',
            'shared_object_path': '{shared_object_anchor}/{shared_object_file}',

            'exe_dir':'bin',
            'exe_basename': '{name}',
            'posix_exe_file': '{exe_basename}',
            'windows_exe_file': '{exe_basename}.exe',
            'exe_file': '{{target_os_{toolkit}}_exe_file}',
            'exe_anchor': '{build_detail_anchor}/{exe_dir}',
            'exe_path': '{exe_anchor}/{exe_file}',

            'lib_dirs': [],
            'libs': {},
        } | (options or {})
        super().__init__(options, dependencies)

    def get_source(self, src_idx):
        '''
        Gets the src_idxth source from options. Ensures the result is a Path.
        '''
        sources = self.opt_list('sources')
        return sources[src_idx]

    def make_src_path(self, src):
        '''
        Makes a full source path out of the src_idxth source from options.
        '''
        return Path(f"{self.opt_str('src_anchor')}/{src}")

    def make_prebuilt_obj_path(self, prebuilt_obj):
        '''
        Make a full path to a prebuilt object file from options.
        '''
        return Path(f"{self.opt_str('prebuilt_obj_anchor')}/{prebuilt_obj}")

    def make_obj_path_from_src(self, src):
        '''
        Makes the full object path from a single source by index.
        '''
        basename = Path(src).stem
        return Path(str(self.opt_str('obj_path', {'obj_basename': basename})))

    def get_all_src_paths(self):
        '''
        Generate te full path for each source file.
        '''
        return [self.make_src_path(src) for src in self.opt_list('sources')]

    def get_all_prebuilt_obj_paths(self):
        '''
        Generate te full path for each prebuilt object file.
        '''
        return [self.make_prebuilt_obj_path(src) for src in self.opt_list('prebuilt_objs')]

    def get_all_object_paths(self):
        '''
        Generate the full path for each target object file.
        '''
        return [self.make_obj_path_from_src(src) for src in self.opt_list('sources')]

    def get_all_src_and_object_paths(self):
        '''
        Generates (source path, object path)s for each source.
        '''
        return zip(self.get_all_src_paths(), self.get_all_object_paths())

    def get_exe_path(self):
        '''
        Makes the full exe path from options.
        '''
        return Path(self.opt_str('exe_path'))

    def get_archive_path(self):
        '''
        Gets the archived library path.
        '''
        return Path(self.opt_str('archive_path'))

    def make_build_command_prefix(self):
        '''
        Makes a partial build command line that several build phases can further augment and use.
        '''
        toolkit = self.opt_str('toolkit')
        if toolkit == 'gnu':
            return self._make_build_command_prefix_gnu()
        if toolkit == 'clang':
            return self._make_build_command_prefix_clang()
        if toolkit == 'visualstudio':
            return self._make_build_command_prefix_vs()
        raise UnsupportedToolkitError(f'Specified toolkit "{toolkit}" is not supported.')

    def _make_build_command_prefix_gnu(self):
        lang = self.opt_str('language').lower()
        ver = self.opt_str('language_version').lower()
        prefix = ''
        if lang == 'c++':
            prefix = f'g++ -std=c++{ver} '
        elif lang == 'c':
            prefix = f'gcc -std=c{ver} '
        else:
            raise UnsupportedLanguageError(f'Specified language "{lang}" is not supported.')
        return self._make_build_command_prefix_gnu_clang(prefix)

    def _make_build_command_prefix_clang(self):
        lang = self.opt_str('language').lower()
        ver = self.opt_str('language_version').lower()
        prefix = ''
        if lang == 'c++':
            prefix = f'clang++ -std=c++{ver} '
        elif lang == 'c':
            prefix = f'clang -std=c{ver} '
        else:
            raise UnsupportedLanguageError(f'Specified language "{lang}" is not supported.')
        return self._make_build_command_prefix_gnu_clang(prefix)

    def _make_build_command_prefix_gnu_clang(self, prefix):
        compile_only = self.opt_str('build_operation') == 'build_obj'
        c = '-c ' if compile_only else ''

        warn = ''.join((f'-W{w} ' for w in self.opt_list('gnuclang_warnings')))

        g = f'-g{self.opt_str("debug_level")} '
        o = f'-O{self.opt_str("optimization")} '
        kf = ' '.join(self.opt_list('kind_flags'))

        defs = ''.join((f'-D{d} ' for d in self.opt_list('definitions')))

        additional_flags = ''.join((str(flag) for flag in self.opt_list('additional_flags')))

        build_string = f'{prefix}{warn}{c}{g}{o} {kf}{defs}{additional_flags} '
        return build_string

    def _make_build_command_prefix_vs(self):
        pass

    def make_archive_command_prefix(self):
        '''
        Makes a partial archive command line.
        '''
        toolkit = self.opt_str('toolkit')
        if toolkit == 'gnu':
            return self._make_archive_command_prefix_gnu()
        if toolkit == 'clang':
            return self._make_archive_command_prefix_gnu()
        if toolkit == 'visualstudio':
            return self._make_archive_command_prefix_vs()
        raise UnsupportedToolkitError(f'Specified toolkit "{toolkit}" is not supported.')

    def _make_archive_command_prefix_gnu(self):
        prefix = 'ar rcs'
        return self._make_archive_command_prefix_gnu_clang(prefix)

    def _make_archive_command_prefix_clang(self):
        prefix = 'llvm-ar rcs'
        return self._make_archive_command_prefix_gnu_clang(prefix)

    def _make_archive_command_prefix_gnu_clang(self, prefix):
        thin = 'P --thin' if self.opt_bool('thin_archive') else ''
        return f'{prefix}{thin} '

    def _make_archive_command_prefix_vs(self):
        return ''

    def make_compile_arguments(self):
        ''' Constructs the inc_dirs portion of a gcc command.'''
        inc_dirs = self.opt_list('include_dirs')
        inc_anchor = self.opt_str('include_anchor')
        pkg_configs = self.opt_list('pkg_config')

        inc_dirs = ''.join((f'-I{inc_anchor}/{inc} ' for inc in inc_dirs))
        pkg_inc_cmd = ('$(pkg-config --cflags-only-I ' +
                   ' '.join(pkg for pkg in pkg_configs) +
                   ')') if len(pkg_configs) > 0 else ''

        pkg_inc_bits_cmd = ('$(pkg-config --cflags-only-other ' +
                   ' '.join(pkg for pkg in pkg_configs) +
                   ')') if len(pkg_configs) > 0 else ''

        return {
            'inc_dirs': inc_dirs + pkg_inc_cmd,
            'pkg_inc_bits': pkg_inc_bits_cmd,
            'relocatable': self.opt_bool('relocatable'),
            'posix_threads': self.opt_bool('posix_threads'),
        }

    def make_link_arguments(self) -> dict:
        ''' Constructs the linking arguments of a gcc command.'''
        lib_bits_cmd = ''

        lib_dirs = self.opt_list('lib_dirs')
        lib_dirs_cmd = ''.join((f'-L{lib_dir} ' for lib_dir in lib_dirs))

        libs_cmd = ''
        libs = self.opt_dict('libs')        # { lib_name: 'archive' or 'shared' or 'package' }
        for lib, method in libs.items():
            if method in ['archive', 'shared_object']:
                libs_cmd += f'-l{lib} '
            elif method == 'package':
                libs_cmd += f'$(pkg-config --libs-only-l {lib}) '
                lib_dirs_cmd += f'$(pkg-config --libs-only-L {lib}) '
                lib_bits_cmd += f'$(pkg-config --libs-only-other {lib}) '

        rpath_cmd = ''
        target_path = str(Path(self.opt_str('target_path')).parent)
        for rpath, origin in self.opt_dict('rpath').items():    # { '../lib', True or False }
            if origin:
                rpath_cmd += f'-Wl,-rpath=\'$ORIGIN{os.path.relpath(rpath, target_path)}\' '
            else:
                rpath_cmd += f'-Wl,-rpath={rpath} '

        return {
            'lib_dirs': lib_dirs_cmd,
            'libs': libs_cmd,
            'lib_bits': lib_bits_cmd,
            'posix_threads': self.opt('posix_threads'),
            'rpath': rpath_cmd,
        }

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

    def make_cmd_compile_src_to_object(self, src_path: Path, obj_path: Path,
                                       just_get_includes: bool = False) -> str:
        ''' Create the full command to build an object from a single source.'''
        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()
        if just_get_includes:
            obj_path = '/dev/null'
        cmd = (f'{prefix}-c {c_args["inc_dirs"]} {c_args["pkg_inc_bits"]} -o {obj_path} '
               f'{" -fPIC" if c_args["relocatable"] else ""}'
               f'{" -pthread" if c_args["posix_threads"] else ""}'
               f' {src_path}'
        )
        if just_get_includes:
            cmd += ' -E -H 1>/dev/null'
        return cmd

    def make_cmd_archive_objects_to_library(self, object_paths: list[Path],
                                            archive_path: Path) -> str:
        ''' Create the full command to build a static lib from objects.'''
        prefix = self.make_archive_command_prefix()
        object_paths_cmd = f'{" ".join((str(obj) for obj in object_paths))} '
        cmd = f'{prefix}{archive_path} {object_paths_cmd}'
        return cmd

    def make_cmd_link_objects_to_shared_object(self, object_paths: list[Path],
                                               shared_object_path: Path) -> str:
        ''' Create the full command to build an exe binary from objects.'''
        prefix = self.make_build_command_prefix()
        l_args = self.make_link_arguments()
        object_paths_cmd = f'{" ".join((str(obj) for obj in object_paths))} '
        cmd = (f'{prefix}-shared -o {shared_object_path} '
               f'-Wl,-soname,{self.opt_str("posix_so_soname")} '
               f'{object_paths_cmd}'
               f'{" -pthread" if l_args["posix_threads"] else ""}{l_args["lib_dirs"]}'
               f'{l_args["lib_bits"]} {l_args["libs"]}{l_args["rpath"]}')
        return cmd

    def make_cmd_link_objects_to_exe(self, object_paths: list[Path], exe_path: Path) -> str:
        ''' Create the full command to build an exe binary from objects.'''
        prefix = self.make_build_command_prefix()
        l_args = self.make_link_arguments()
        object_paths_cmd = f'{" ".join((str(obj) for obj in object_paths))} '
        cmd = (f'{prefix}-o {exe_path} {object_paths_cmd}'
               f'{" -pthread" if l_args["posix_threads"] else ""}{l_args["lib_dirs"]}'
               f'{l_args["lib_bits"]} {l_args["libs"]}{l_args["rpath"]}')
        return cmd

    def make_cmd_compile_srcs_to_shared_object(self, src_paths: list[Path],
                                               shared_object_path: Path,
                                               just_get_includes: bool = False) -> str:
        ''' Create the full command to build an object form a single source.'''
        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()
        l_args = self.make_link_arguments()
        if just_get_includes:
            shared_object_path = '/dev/null'
        src_paths_cmd = f'{" ".join((str(src) for src in src_paths))} '
        cmd = (f'{prefix}-shared {c_args["inc_dirs"]} {c_args["pkg_inc_bits"]} '
               f'-o {shared_object_path} '
               f'{" -fPIC" if c_args["relocatable"] else ""}'
               f'-Wl,-soname,{self.opt_str("posix_so_soname")} '
               f'{" -pthread" if l_args["posix_threads"] else ""}'
               f'{src_paths_cmd}'
               f'{l_args["lib_dirs"]} {l_args["lib_bits"]} {l_args["libs"]}'
               f'{l_args["rpath"]}')
        if just_get_includes:
            cmd += ' -E -H 1>/dev/null'
        return cmd

    def make_cmd_compile_srcs_to_exe(self, src_paths: list[Path], exe_path: Path,
                                     just_get_includes: bool = False) -> str:
        ''' Create the full command to build an object form a single source.'''
        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()
        l_args = self.make_link_arguments()
        if just_get_includes:
            exe_path = '/dev/null'
        src_paths_cmd = f'{" ".join((str(src) for src in src_paths))} '
        cmd = (f'{prefix} {c_args["inc_dirs"]} {c_args["pkg_inc_bits"]} -o {exe_path} '
               f'{" -fPIC" if c_args["relocatable"] else ""}'
               f'{" -pthread" if l_args["posix_threads"] else ""}{l_args["lib_dirs"]}'
               f'{src_paths_cmd}'
               f'{l_args["lib_bits"]} {l_args["libs"]}{l_args["rpath"]}')
        if just_get_includes:
            cmd += ' -E -H 1>/dev/null'
        return cmd

    def parse_include_report(self, report):
        ''' Turn GCC's -H output into a list of include paths.'''
        paths = []
        for line in report.splitlines():
            if line.startswith('.'):
                line = line.lstrip('. ')
                paths.append(Path(line))
        return paths

    def get_includes_src_to_object(self, src_path: Path, obj_path: Path) -> list[Path]:
        ''' Get all the headers used by the given src_path, including system headers.'''
        cmd = self.make_cmd_compile_src_to_object(src_path, obj_path, True)
        ret, _, err = do_shell_command(cmd)
        if ret == 0:
            return self.parse_include_report(err)
        raise ValueError('Header discovery failed.')

    def get_includes_srcs_to_exe(self, src_paths: list[Path], obj_path: Path) -> list[Path]:
        ''' Get all the headers used by the given src_path, including system headers.'''
        cmd = self.make_cmd_compile_srcs_to_exe(src_paths, obj_path, True)
        ret, _, err = do_shell_command(cmd)
        if ret == 0:
            return self.parse_include_report(err)
        raise ValueError('Header discovery failed.')

    def do_step_compile_src_to_object(self, action: Action, depends_on: Steps, src_path: Path,
                                      inc_paths: list[Path], obj_path: Path) -> Step:
        '''
        Perform a C or C++ source compile operation as an action step.
        '''
        def act(cmd: str, src_path: Path, inc_paths: list[Path], obj_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None

            if not src_path.exists():
                step_result = ResultCode.MISSING_INPUT
                step_notes = src_path
            else:
                if not obj_path.exists() or any(input_path_is_newer(dep_path, obj_path)
                                                for dep_path in [src_path, *inc_paths]):
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = self.make_cmd_compile_src_to_object(src_path, obj_path)
        step = Step('compile', depends_on, [src_path], [obj_path],
                             partial(act, cmd, src_path, inc_paths, obj_path), cmd)
        action.set_step(step)
        return step

    def do_step_archive_objects_to_library(self, action: Action, depends_on: Steps,
                                           object_paths: list[Path], archive_path: Path) -> Step:
        '''
        Perform an archive operaton on built object files.
        '''
        def act(cmd, object_paths, archive_path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            missing_objs = []

            for obj_path in object_paths:
                if not obj_path.exists():
                    missing_objs.append(obj_path)
            if len(missing_objs) > 0:
                step_result = ResultCode.MISSING_INPUT
                step_notes = missing_objs
            else:
                archive_exists = archive_path.exists()
                must_build = not archive_exists
                for obj_path in object_paths:
                    if not archive_exists or input_path_is_newer(obj_path, archive_path):
                        must_build = True
                if must_build:
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = self.make_cmd_archive_objects_to_library(object_paths, archive_path)
        step = Step('archive', depends_on, object_paths, [archive_path],
                    partial(act, cmd, object_paths, archive_path), cmd)
        action.set_step(step)
        return step

    def do_step_link_objects_to_shared_object(self, action: Action, depends_on: Steps,
                                    object_paths: list[Path], shared_object_path: Path) -> Step:
        '''
        Perform a link to shared object operation as an action step.
        '''
        def act(cmd, object_paths, exe_path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            missing_objs = []

            for obj_path in object_paths:
                if not obj_path.exists():
                    missing_objs.append(obj_path)
            if len(missing_objs) > 0:
                step_result = ResultCode.MISSING_INPUT
                step_notes = missing_objs
            else:
                exe_exists = exe_path.exists()
                must_build = not exe_exists
                for obj_path in object_paths:
                    if not exe_exists or input_path_is_newer(obj_path, exe_path):
                        must_build = True
                if must_build:
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = self.make_cmd_link_objects_to_shared_object(object_paths, shared_object_path)
        step = Step('link to shared object', depends_on, object_paths, [shared_object_path],
                    partial(act, cmd, object_paths, shared_object_path), cmd)
        action.set_step(step)
        return step

    def do_step_link_objects_to_exe(self, action: Action, depends_on: Steps,
                                    object_paths: list[Path], exe_path: Path) -> Step:
        '''
        Perform a link to executable operation as an action step.
        '''
        def act(cmd, object_paths, exe_path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            missing_objs = []

            for obj_path in object_paths:
                if not obj_path.exists():
                    missing_objs.append(obj_path)
            if len(missing_objs) > 0:
                step_result = ResultCode.MISSING_INPUT
                step_notes = missing_objs
            else:
                exe_exists = exe_path.exists()
                must_build = not exe_exists
                for obj_path in object_paths:
                    if not exe_exists or input_path_is_newer(obj_path, exe_path):
                        must_build = True
                if must_build:
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = self.make_cmd_link_objects_to_exe(object_paths, exe_path)
        step = Step('link', depends_on, object_paths, [exe_path],
                    partial(act, cmd, object_paths, exe_path), cmd)
        action.set_step(step)
        return step

    def do_step_compile_srcs_to_exe(self, action: Action, depends_on: Steps,
                                    src_paths: list[Path], inc_paths: list[Path],
                                    exe_path: Path) -> Step:
        '''
        Perform a multiple C or C++ source compile to executable operation as an action step.
        '''
        def act(cmd, src_paths: list[Path], inc_paths: list[Path], exe_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            missing_srcs = []

            for src_path in src_paths:
                if not src_path.exists():
                    missing_srcs.append(src_path)
            if len(missing_srcs) > 0:
                step_result = ResultCode.MISSING_INPUT
                step_notes = missing_srcs
            else:
                exe_exists = exe_path.exists()
                if not exe_exists or any(input_path_is_newer(dep_path, exe_path)
                                         for dep_path in [*src_paths, *inc_paths]):
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = self.make_cmd_compile_srcs_to_exe(src_paths, inc_paths, exe_path)
        step = Step('compile and link', depends_on, src_paths, [exe_path],
                    partial(act, cmd, src_paths, exe_path), cmd)
        action.set_step(step)
        return step

    def do_step_softlink_soname_to_real_name(self, action: Action, depends_on: Steps) -> Step:
        ''' Create the standard soname softlink for shared objects.'''
        def act(cmd: str, realname: Path) -> Result:
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if realname.exists():
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        anchor = Path(self.opt_str('shared_object_anchor')) 
        realname = anchor / Path(self.opt_str("posix_so_real_name"))
        soname = anchor / Path(self.opt_str("posix_so_soname"))
        cmd = f'ln -s {realname} {soname}'
        step = Step('create softlink', depends_on, [realname], [soname],
                             partial(act, cmd, realname), cmd)
        action.set_step(step)
        return step

    def do_step_softlink_linker_name_to_soname(self, action: Action, depends_on: Steps) -> Step:
        ''' Create the standard linker name softlink for shared objects.'''
        def act(cmd: str, realname: Path) -> Result:
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if realname.exists():
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        anchor = Path(self.opt_str('shared_object_anchor')) 
        soname = anchor / Path(self.opt_str("posix_so_soname"))
        linkername = anchor / Path(self.opt_str("posix_so_linker_name"))
        cmd = f'ln -s {soname} {linkername}'
        step = Step('create softlink', depends_on, [soname], [linkername],
                             partial(act, cmd, soname), cmd)
        action.set_step(step)
        return step

    def do_action_clean_build_directory(self, action: Action) -> Step:
        '''
        Wipes out the build directory.
        '''
        return self.do_step_delete_directory(action, None, Path(self.opt_str("build_anchor")))
