''' Contains the BuildPhase intermediate phase class. '''

from functools import partial
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

            'inc_dir': '.',
            'include_anchor': '{project_anchor}/{inc_dir}',
            'include_dirs': ['include'],

            'src_dir': 'src',
            'src_anchor': '{project_anchor}/{src_dir}',
            'sources': [],

            'prebuilt_obj_dir': 'prebuilt_obj',
            'prebuilt_obj_anchor': '{project_anchor}/{prebuilt_obj_dir}',
            'prebuilt_objs': [],

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

            'exe_dir':'bin',
            'exe_basename': '{name}',
            'posix_exe_file': '{exe_basename}',
            'windows_exe_file': '{exe_basename}.exe',
            'exe_file': '{{target_os_{toolkit}}_exe_file}',
            'exe_anchor': '{build_detail_anchor}/{exe_dir}',
            'exe_path': '{exe_anchor}/{exe_file}',

            'lib_dirs': [],
            'libs': [],
            'shared_libs': [],
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
            'posix_threads': self.opt('posix_threads'),
        }

    def make_link_arguments(self):
        ''' Constructs the linking arguments of a gcc command.'''
        pkg_configs = self.opt_list('pkg_config')

        pkg_dirs_cmd = ('$(pkg-config --libs-only-L ' +
                   ' '.join(pkg for pkg in pkg_configs) +
                   ')') if len(pkg_configs) > 0 else ''
        pkg_libs_cmd = ('$(pkg-config --libs-only-l ' +
                   ' '.join(pkg for pkg in pkg_configs) +
                   ')') if len(pkg_configs) > 0 else ''
        pkg_libs_bits_cmd = ('$(pkg-config --libs-only-other ' +
                   ' '.join(pkg for pkg in pkg_configs) +
                   ')') if len(pkg_configs) > 0 else ''

        lib_dirs = self.opt_list('lib_dirs')
        lib_dirs_cmd = ''.join((f'-L{lib_dir} ' for lib_dir in lib_dirs))
        lib_dirs_cmd += pkg_dirs_cmd

        static_libs = self.opt_list('libs')
        static_libs_cmd = ''.join((f'-l{lib} ' for lib in static_libs))
        static_libs_cmd += pkg_libs_cmd
        #if len(static_libs_cmd) > 0:
        #    static_libs_cmd = f'-Wl,-static {static_libs_cmd}'

        # TODO: Ensure this is all kinda correct. I'm learning about rpath/$ORIGIN.
        shared_libs = self.opt_list('shared_libs')
        shared_libs_cmd = ''.join((f'-l{so} ' for so in shared_libs))
        #if len(shared_libs_cmd) > 0:
        #    shared_libs_cmd = f'-Wl,-dynamic {shared_libs_cmd} -Wl,-rpath,$ORIGIN -Wl,-z,origin'

        return {
            'lib_dirs': lib_dirs_cmd,
            'static_libs': static_libs_cmd,
            'shared_libs': shared_libs_cmd,
            'pkg_libs_bits': pkg_libs_bits_cmd,
            'posix_threads': self.opt('posix_threads'),
        }

    def do_step_delete_file(self, action: Action, depends_on: Steps, path: Path) -> Step:
        '''
        Perfoems a file deletion operation as an action step.
        '''
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
        step = Step('delete file', depends_on, [path], [], cmd,
                             partial(act, cmd=cmd, path=path))
        action.set_step(step)
        return step

    def do_step_delete_directory(self, action: Action, depends_on: Steps, direc: Path) -> Step:
        '''
        Perfoems a file deletion operation as an action step.
        '''
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
        step = Step('delete directory', depends_on, [direc], [], cmd,
                             partial(act, cmd=cmd, direc=direc))
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
        step = Step('create directory', depends_on, [], [new_dir], cmd,
                             partial(act, cmd=cmd, new_dir=new_dir))
        action.set_step(step)
        return step

    def do_step_compile_src_to_object(self, action: Action, depends_on: Steps, prefix: str, args: list[str],
                                      src_path: Path, obj_path: Path) -> Step:
        '''
        Perform a C or C++ source compile operation as an action step.
        '''
        def act(cmd: str, src_path: Path, obj_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None

            if not src_path.exists():
                step_result = ResultCode.MISSING_INPUT
                step_notes = src_path
            else:
                if not obj_path.exists() or input_path_is_newer(src_path, obj_path):
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = (f'{prefix}-c {args["inc_dirs"]} {args["pkg_inc_bits"]} -o {obj_path} '
               f'{src_path}{" -pthread" if args["posix_threads"] else ""}')
        step = Step('compile', depends_on, [src_path], [obj_path], cmd,
                             partial(act, src_path, obj_path))
        action.set_step(step)
        return step

    def do_step_archive_objects_to_library(self, action: Action, depends_on: Steps, prefix: str, archive_path: Path,
                                           object_paths: list[Path]) -> Step:
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

        object_paths_cmd = f'{" ".join((str(obj) for obj in object_paths))} '
        cmd = f'{prefix}{archive_path} {object_paths_cmd}'
        step = Step('archive', depends_on, object_paths, [archive_path], cmd,
                    partial(act, object_paths, archive_path))
        action.set_step(step)
        return step

    def do_step_link_objects_to_exe(self, action: Action, depends_on: Steps, prefix: str, args: dict,
                                    exe_path: Path, object_paths: list[Path]) -> Step:
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

        object_paths_cmd = f'{" ".join((str(obj) for obj in object_paths))} '
        cmd = (f'{prefix}-o {exe_path} {object_paths_cmd}'
               f'{" -pthread" if args["posix_threads"] else ""}{args["lib_dirs"]}'
               f'{args["pkg_libs_bits"]} {args["static_libs"]}{args["shared_libs"]}')
        step = Step('link', depends_on, object_paths, [exe_path], cmd,
                    partial(act, object_paths, exe_path))
        action.set_step(step)
        return step

    def do_step_compile_srcs_to_exe(self, action: Action, depends_on: Steps, prefix: str,
                                    args: dict, src_paths: list[Path], exe_path: Path) -> Step:
        '''
        Perform a multiple C or C++ source compile to executable operation as an action step.
        '''
        def act(cmd, src_paths, exe_path):
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
                must_build = not exe_exists
                for src_path in src_paths:
                    if not exe_exists or input_path_is_newer(src_path, exe_path):
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

        src_paths_cmd = f'{" ".join((str(src) for src in src_paths))} '
        cmd = (f'{prefix} {args["inc_dirs"]} {args["pkg_inc_bits"]} -o {exe_path} '
               f'{" -pthread" if args["posix_threads"] else ""}'
               f'{src_paths_cmd}{args["lib_dirs"]} {args["pkg_libs_bits"]} '
               f'{args["static_libs"]}{args["shared_libs"]}')
        step = Step('compile and link', depends_on, src_paths, [exe_path], cmd,
                    partial(act, src_paths, exe_path))
        action.set_step(step)
        return step

    def do_action_clean_build_directory(self, action: Action, depends_on: Steps) -> Step:
        '''
        Wipes out the build directory.
        '''
        return self.do_step_delete_directory(action, depends_on,
                                             Path(self.opt_str("build_anchor")))

