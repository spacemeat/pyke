''' CMake project builder phase. '''

from functools import partial
from pathlib import Path
from ..action import Action, Step, Result, ResultCode, FileData
from .c_family_build import CFamilyBuildPhase
from ..utilities import do_shell_command

class CMakeRepoPhase(CFamilyBuildPhase):
    ''' Phase to build a CMake project.'''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(options, dependencies)
        self.options |= {
            'name': 'CMake-build',
            'cmake_args': '',
            'makes': {},
        }
        self.options |= (options or {})

    def compute_file_operations(self):
        build_detail_anchor = Path(self.opt_str('build_detail_anchor'))

        dirs = self.get_direct_dependency_output_files('dir')
        if len(dirs) > 0:
            build_detail_anchor = Path(dirs[0].path)

        self.record_file_operation(
            None,
            FileData(build_detail_anchor, 'dir', self),
            'create directory')

        for artifact, file_type in self.opt_dict('makes').items():
            self.record_file_operation(
                None,
                FileData(build_detail_anchor / artifact, file_type, self),
                'build')

    def do_step_cmake(self, action: Action, depends_on: list[Step] | Step | None, cmake_path: Path):
        ''' Runs cmake to generate Makefile.'''
        def act(cmd: str, cmake_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            missing_objs = []

            if not cmake_path.exists():
                missing_objs.append(cmake_path)
                step_result = ResultCode.MISSING_INPUT
                step_notes = missing_objs
            else:
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED

            return Result(step_result, str(step_notes))

        build_detail_anchor = self.opt_str('build_detail_anchor')
        dirs = self.files.get_output_files('dir')
        if len(dirs) > 0:
            build_detail_anchor = dirs[0].path

        project_dir = cmake_path.parent
        cmake_args = self.opt_str('cmake_args')
        cmd = f'cmake -B {build_detail_anchor} -S {project_dir}{cmake_args}'
        step = Step('cmake', depends_on, [cmake_path], [],
                    partial(act, cmd, cmake_path), cmd)
        action.set_step(step)
        return step

    def do_step_clean(self, action: Action, depends_on: list[Step] | Step | None) -> Step:
        ''' Performs a shell command as an action step. '''
        def act(cmd: str, make_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            missing_objs = []

            if not make_path.exists():
                missing_objs.append(make_path)
                step_result = ResultCode.MISSING_INPUT
                step_notes = missing_objs
            else:
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED

            return Result(step_result, str(step_notes))

        build_detail_anchor = self.opt_str('build_detail_anchor')
        dirs = self.files.get_output_files('dir')
        if len(dirs) > 0:
            build_detail_anchor = dirs[0].path

        make_path = Path(build_detail_anchor) / 'Makefile'
        cmd = f'cd {build_detail_anchor} && make clean'
        step = Step('clean', depends_on, [make_path], [],
                    partial(act, cmd, make_path), cmd)
        action.set_step(step)
        return step

    def do_step_build(self, action: Action, depends_on: list[Step] | Step | None) -> Step:
        ''' Performs a shell command as an action step. '''
        def act(cmd: str, make_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            missing_objs = []

            if not make_path.exists():
                missing_objs.append(make_path)
                step_result = ResultCode.MISSING_INPUT
                step_notes = missing_objs
            else:
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED

            return Result(step_result, str(step_notes))

        build_detail_anchor = self.opt_str('build_detail_anchor')
        dirs = self.files.get_output_files('dir')
        if len(dirs) > 0:
            build_detail_anchor = dirs[0].path

        make_path = Path(build_detail_anchor) / 'Makefile'
        cmd = f'cd {build_detail_anchor} && make'
        step = Step('build', depends_on, [make_path], [],
                    partial(act, cmd, make_path), cmd)
        action.set_step(step)
        return step

    def do_action_clean(self, action: Action):
        ''' Runs cmake, then make clean to clean the project. '''
        step_mkdir = self.do_step_create_directory(action, None,
                                                   Path(self.opt_str('build_detail_anchor')))
        files = self.get_direct_dependency_output_files('cmake_makefile')
        if len(files) > 0:
            cmake_path = files[0].path
            step_cmake = self.do_step_cmake(action, step_mkdir, Path(cmake_path))
            self.do_step_clean(action, step_cmake)

    def do_action_build(self, action: Action):
        ''' Runs cmake, then make to build the project.'''
        step_mkdir = self.do_step_create_directory(action, None,
                                                   Path(self.opt_str('build_detail_anchor')))
        files = self.get_direct_dependency_output_files('cmake_makefile')
        if len(files) > 0:
            cmake_path = files[0].path
            step_cmake = self.do_step_cmake(action, step_mkdir, Path(cmake_path))
            self.do_step_build(action, step_cmake)
