''' Contains the BuildPhase intermediate phase class. '''

from pathlib import Path

from ..action import ActionStep, ResultCode
from ..utilities import (UnsupportedToolkitError, UnsupportedLanguageError, input_is_newer,
                         do_shell_command)
from .phase import Phase


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
        return Path(str(self.sopt('obj_path', {'obj_basename': basename})))

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
        return Path(str(self.sopt('exe_path')))

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
