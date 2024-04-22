''' Contains the BuildPhase intermediate phase class. '''

from functools import partial
import os
from pathlib import Path
import shlex
from typing import TypeAlias

from ..action import Action, Step, Result, ResultCode
from ..utilities import (UnsupportedToolkitError, UnsupportedLanguageError,
                         do_interactive_command, uniquify_list,
                         input_path_is_newer, do_shell_command)
from .phase import Phase

Steps: TypeAlias = list[Step] | Step | None


class CFamilyBuildPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(None, dependencies)
        self.options |= {
            # Sets the source language. c|c++
            'language': 'c++',
            # Sets the source language version.
            'language_version': '23',
            'tool_args_gnu': 'gnuclang',
            'tool_args_clang': 'gnuclang',
            'tool_args_visualstudio': 'visualstudio',
            # Sets the warning flags for gnu and clang tools.
            'gnuclang_warnings': ['all', 'extra', 'error'],
            # Sets the debug level (-gn flga) for gnu and clang tools when in debug mode.
            'gnuclang_debug_debug_level': '2',
            # Sets the optimization level (-On flag) for gnu and clang tools when in debug mode.
            'gnuclang_debug_optimization': 'g',
            # Sets debug mode-specific flags for gnu and clang tools.
            'gnuclang_debug_flags': ['-fno-inline', '-fno-lto', '-DDEBUG'],
            # Sets the debug level (-gn flga) for gnu and clang tools when in release mode.
            'gnuclang_release_debug_level': '0',
            # Sets the optimization level (-On flag) for gnu and clang tools when in release mode.
            'gnuclang_release_optimization': '2',
            # Sets release mode-specific flags for gnu and clang tools.
            'gnuclang_release_flags': ['-DNDEBUG'],
            # Any additional compiler flags for gnu and clang tools.
            'gnuclang_additional_flags': [],
            ##'visualstudio_warnings': [],
            ##'visualstudio_debug_debug_level': '',
            ##'visualstudio_debug_optimization': '',
            ##'visualstudio_debug_flags': [],
            ##'visualstudio_release_debug_level': '',
            ##'visualstudio_release_optimization': '',
            ##'visualstudio_release_flags': [],
            ##'visualstudio_additional_flags': [],
            'warnings': '{{tool_args_{toolkit}}_warnings}',
            'debug_level': '{{tool_args_{toolkit}}_{kind}_debug_level}',
            'optimization': '{{tool_args_{toolkit}}_{kind}_optimization}',
            'kind_flags': '{{tool_args_{toolkit}}_{kind}_flags}',
            'additional_flags': '{{tool_args_{toolkit}}_additional_flags}',
            # Macro definitions passed to the preprocessor.
            'definitions': [],
            # Enables multithreaded builds for gnu and clang tools.
            'posix_threads': False,
            # Whether to make the code position-independent (-fPIC for gnu and clang tools).
            'relocatable_code': False,

            # Whether to reference dependency shared objects with -rpath.
            'rpath_deps': True,
            # Whether to condition the build for dependencies which can be relatively placed.
            # (-rpath=$ORIGIN)
            'moveable_binaries': True,
            ##'export_dynamic': False,
            ##'symbol_visibility': 'hidden', # see https://gcc.gnu.org/wiki/Visibility

            'inc_dir': '.',
            'include_anchor': '{project_anchor}/{inc_dir}',
            # List of directories to search for project headers, relative to {include_anchor}.
            'include_dirs': ['include'],

            'src_dir': 'src',
            'src_anchor': '{project_anchor}/{src_dir}',
            # List of source files relative to {src_anchor}.
            'sources': [],

            # List of directories to search for library archives or shared objects.
            'lib_dirs': [],
            # Collection of library archives or shared objects or pkg-configs to link. Format is:
            # { 'foo', type } where type is 'archive' | 'shared_object' | 'package'
            'libs': {},

            # Specifies the directory where prebuilt objects (say from a binary distribution) are
            # found.
            'prebuilt_obj_dir': 'prebuilt_obj',
            'prebuilt_obj_anchor': '{project_anchor}/{prebuilt_obj_dir}',
            # List of prebuilt objects to link against.
            'prebuilt_objs': [],

            'target_path': '',

            # Target-specific build directory.
            'build_detail': '{group}.{toolkit}.{kind}',
            'build_detail_anchor': '{build_anchor}/{build_detail}',

            # Directory where intermediate artifacts like objects are placed.
            'obj_dir': 'int',
            # The base filename of a taret object file.
            'obj_basename': '',
            # How object files are named on a POSIX system.
            'posix_obj_file': '{obj_basename}.o',
            ##'windows_obj_file': '{obj_basename}.obj',
            'obj_file': '{{target_os}_obj_file}',
            'obj_anchor': '{build_detail_anchor}/{obj_dir}',
            'obj_path': '{obj_anchor}/{obj_file}',

            # Whether to build a 'thin' archive. (See ar(1).)
            'thin_archive': False,

            # Where to emplace archive library artifacts.
            'archive_dir':'lib',
            # The base filename of a target archive file.
            'archive_basename': '{name}',
            # How archives are named on a POSIX system.
            'posix_archive_file': 'lib{archive_basename}.a',
            ##'windows_archive_file': '{archive_basename}.lib',
            'archive_file': '{{target_os}_archive_file}',
            'archive_anchor': '{build_detail_anchor}/{archive_dir}',
            'archive_path': '{archive_anchor}/{archive_file}',

            # Collection of library search paths built into the target binary. Formatted like:
            # { 'directory': True }
            # Where the boolean value specifies whether to use $ORIGIN. See the -rpath option
            # in the gnu and clang tools. Note that this is automatically managed for dependency
            # library builds.
            'rpath': {},

            # Where to emplace shared object artifacts.
            'shared_object_dir': 'lib',
            # The base filename of a shared object file.
            'shared_object_basename': '{name}',
            # Whether to place the version number into the artifact, and create the standard soft
            # links.
            'generate_versioned_sonames': False,
            # Shared object major version number.
            'so_major': '{version_major}',
            # Shared object minor version number.
            'so_minor': '{version_minor}',
            # Shared object patch version number.
            'so_patch': '{version_patch}',
            # How shared objects are unversioned-naemd on POSIX systems.
            'posix_so_linker_name': 'lib{shared_object_basename}.so',
            # How shared objects are major-version-only named on POSIX systems.
            'posix_so_soname': '{posix_so_linker_name}.{so_major}',
            # How shared objects are full-version named on POSIX systems.
            'posix_so_real_name': '{posix_so_soname}.{so_minor}.{so_patch}',
            # The actual target name for a shared object. May be redefined for some project types.
            'posix_shared_object_file': '{posix_so_linker_name}',
            ##'windows_shared_object_file': '{shared_object_basename}.dll',
            'shared_object_file': '{{target_os}_shared_object_file}',
            'shared_object_anchor': '{build_detail_anchor}/{shared_object_dir}',
            'shared_object_path': '{shared_object_anchor}/{shared_object_file}',

            # Where to emplace executable artifacts.
            'exe_dir':'bin',
            # The base filename of a target executable file.
            'exe_basename': '{name}',
            # How executable files are named on POSIX systems.
            'posix_exe_file': '{exe_basename}',
            ##'windows_exe_file': '{exe_basename}.exe',
            'exe_file': '{{target_os}_exe_file}',
            'exe_anchor': '{build_detail_anchor}/{exe_dir}',
            'exe_path': '{exe_anchor}/{exe_file}',

            # Arguments to pass when running a built executable.
            'run_args': ''
        }
        self.options |= (options or {})

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
        warn = ''.join((f'-W{w} ' for w in self.opt_list('gnuclang_warnings')))

        g = f'-g{self.opt_str("debug_level")} '
        o = f'-O{self.opt_str("optimization")} '
        kf = ' '.join(self.opt_list('kind_flags'))

        additional_flags = ''.join((str(flag) for flag in self.opt_list('additional_flags')))

        build_string = f'{prefix}{warn}{g}{o}{kf} {additional_flags} '
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
        pkg_configs = []
        for lib, method in self.opt_dict('libs').items():
            if method in ['archive', 'package']:
                pkg_configs = self.opt_list(lib)

        defs = ''.join((f'-D{d} ' for d in self.opt_list('definitions')))

        inc_dirs = ''.join((f'-I{inc_anchor}/{inc} ' for inc in inc_dirs))
        pkg_inc_cmd = ('$(pkg-config --cflags-only-I ' +
                   ' '.join(pkg for pkg in pkg_configs) +
                   ') ') if len(pkg_configs) > 0 else ''

        pkg_inc_bits_cmd = ('$(pkg-config --cflags-only-other ' +
                   ' '.join(pkg for pkg in pkg_configs) +
                   ') ') if len(pkg_configs) > 0 else ''

        return {
            'defs': defs,
            'inc_dirs': inc_dirs + pkg_inc_cmd,
            'pkg_inc_bits': pkg_inc_bits_cmd,
            'relocatable_code': self.opt_bool('relocatable_code'),
            'posix_threads': self.opt_bool('posix_threads'),
        }

    def inherit_libs(self):
        ''' Computes lib_dirs and libs from dependency library phases.'''
        archive_objs = self.get_direct_dependency_output_files('archive')
        shared_objs = self.get_direct_dependency_output_files('shared_object')
        # fill in lib_dirs
        lib_dirs = [ *[str(file.path.parent) for file in archive_objs],
                     *[str(file.path.parent) for file in shared_objs] ]
        lib_dirs.extend(self.opt_list('lib_dirs'))
        lib_dirs = uniquify_list(lib_dirs)

        # fill in rpath
        rpath = {}
        moveable = self.opt_bool('moveable_binaries')
        if self.opt_bool('rpath_deps'):
            rpath = ({ str(file.path.parent): moveable for file in shared_objs } |
                     self.opt_dict('rpath'))

        # fill in libs
        libs = {}
        libs |= {file.generating_phase.opt_str('archive_basename'): 'archive'
                        for file in archive_objs}
        libs |= {file.generating_phase.opt_str('shared_object_basename'): 'shared_object'
                        for file in shared_objs}
        return (lib_dirs, rpath, libs)

    def make_link_arguments(self) -> dict:
        ''' Constructs the linking arguments of a gcc command.'''
        lib_dirs, rpaths, libs = self.inherit_libs()
        lib_bits_cmd = ''
        lib_dirs_cmd = ''.join((f'-L{lib_dir} ' for lib_dir in lib_dirs))
        libs_cmd = ''
        for lib, method in {**libs, **self.opt_dict('libs')}.items():
            if method in ['archive', 'shared_object']:
                libs_cmd += f'-l{lib} '
            elif method == 'package':
                libs_cmd += f'$(pkg-config --libs-only-l {lib}) '
                lib_dirs_cmd += f'$(pkg-config --libs-only-L {lib}) '
                lib_bits_cmd += f'$(pkg-config --libs-only-other {lib}) '

        rpath_cmd = ''
        target_path = str(Path(self.opt_str('target_path')).parent)
        for rpath, origin in rpaths.items():
            if origin:
                path = os.path.relpath(rpath, target_path)
                rpath_cmd += f'-Wl,-rpath=\'$ORIGIN/{path}\' '
            else:
                rpath_cmd += f'-Wl,-rpath={rpath} '

        return {
            'lib_dirs': lib_dirs_cmd,
            'libs': libs_cmd,
            'lib_bits': lib_bits_cmd,
            'posix_threads': self.opt('posix_threads'),
            'rpath': rpath_cmd,
        }

    def make_cmd_compile_src_to_object(self, src_path: Path, obj_path: Path,
                                       just_get_includes: bool = False) -> str:
        ''' Create the full command to build an object from a single source.'''
        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()
        if just_get_includes:
            obj_path = Path('/dev/null')
        cmd = (f'{prefix}-c {c_args["defs"]} {c_args["inc_dirs"]} {c_args["pkg_inc_bits"]}'
               f'{"-fPIC " if c_args["relocatable_code"] else ""}'
               f'{"-pthread " if c_args["posix_threads"] else ""}'
               f'-o {obj_path} {src_path}'
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
        soname = (f'-Wl,-soname,{self.opt_str("posix_so_soname")} '
                  if self.opt_bool('generate_versioned_sonames') else '')
        cmd = (f'{prefix}-shared -o {shared_object_path} '
               f'{soname}'
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
        if not src_path.exists():
            return []
        cmd = self.make_cmd_compile_src_to_object(src_path, obj_path, True)
        ret, _, err = do_shell_command(cmd)
        if ret == 0:
            return self.parse_include_report(err)
        raise ValueError('Header discovery failed.')

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

            return Result(step_result, str(step_notes))

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

            return Result(step_result, str(step_notes))

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

            return Result(step_result, str(step_notes))

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

            return Result(step_result, str(step_notes))

        cmd = self.make_cmd_link_objects_to_exe(object_paths, exe_path)
        step = Step('link', depends_on, object_paths, [exe_path],
                    partial(act, cmd, object_paths, exe_path), cmd)
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
                step_result = ResultCode.MISSING_INPUT

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
                step_result = ResultCode.MISSING_INPUT

            return Result(step_result, step_notes)

        anchor = Path(self.opt_str('shared_object_anchor'))
        soname = anchor / Path(self.opt_str("posix_so_soname"))
        linkername = anchor / Path(self.opt_str("posix_so_linker_name"))
        cmd = f'ln -s {soname} {linkername}'
        step = Step('create softlink', depends_on, [soname], [linkername],
                             partial(act, cmd, soname), cmd)
        action.set_step(step)
        return step

    def do_step_run_executable(self, action: Action, depends_on: Steps, exe_path: Path) -> Step:
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
        step = Step('run executable', depends_on, [exe_path], [], partial(act, cmd, exe_path))
        action.set_step(step)
        return step
