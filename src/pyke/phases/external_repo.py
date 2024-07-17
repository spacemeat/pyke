''' This phase syncs an external repository to a specific version. '''

from functools import partial
from pathlib import Path
from typing import TypeAlias

from ..action import Action, Step, Result, ResultCode, FileData
from ..utilities import do_shell_command
from .phase import Phase

Steps: TypeAlias = list[Step] | Step | None

class ExternalRepoPhase(Phase):
    '''
    Phase class for syncing a remote repository.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(None, dependencies)
        self.options |= {
            'name': '',
            'package_name': '',
            'repo_name': '',
            'repo_version': '',
            'service': 'github',        # or gitlab, or some mercurial site, or www, ...
            'package_kind': 'tarball',
            'compression_kind': 'gzip',
            'tarball_extension': '.tar',
            'gzip_extension': '.gz',
            'package_extension': '{{package_kind}_extension}{{compression_kind}_extension}',
            'target_hard_dir': '{external_repos_anchor}/{package_name}-{repo_version}',
            'target_link_dir': '{external_repos_anchor}/{package_name}',
            'compressed_file': '{package_name}-{repo_version}{package_extension}',
            'compressed_path': '{external_repos_anchor}/{compressed_file}',

            'repo_url': '{{service}_url}',
            'github_url': ('https://api.github.com/repos/{repo_name}'
                           '/tarball/{repo_version}'),

            'build_anchor': '{target_link_dir}/{build_dir}',
            # There may not be any such files; this is a sane default.
            'pyke_makefiles': {'project': '{target_link_dir}/make.py'},
            'using_pyke_makefile': '',
            # There may not be any such files; this is a sane default.
            'cmake_makefiles': {'project': '{target_link_dir}/CMakeLists.txt'},
            'using_cmake_makefile': '',
        }
        self.options |= (options or {})

    def compute_file_operations(self):
        ''' Implement this in any phase that uses input files or generates output files.'''
        using_pyke_makefile = self.opt_str('using_pyke_makefile')
        if using_pyke_makefile != '':
            pyke_makefile_path = self.opt_dict('pyke_makefiles')[using_pyke_makefile]
            self.record_file_operation(
                None,
                FileData(pyke_makefile_path, 'pyke_makefile', self),
                'softlink')

        using_cmake_makefile = self.opt_str('using_cmake_makefile')
        if using_cmake_makefile != '':
            cmake_makefile_path = self.opt_dict('cmake_makefiles')[using_cmake_makefile]
            self.record_file_operation(
                None,
                FileData(cmake_makefile_path, 'cmake_makefile', self),
                'softlink')

        project_anchor = self.opt_str('build_detail_anchor')
        self.record_file_operation(
            None,
            FileData(project_anchor, 'dir', self),
            'create directory')

    def make_repo_url(self):
        return self.opt_str('repo_url')

    def make_cmd_package_request(self):
        if self.opt_str('service') == 'github':
            return self.make_cmd_package_request_github()

        url = self.opt_str('repo_url')
        target_path = self.opt_str('compressed_path')
        return f'curl -L {url} --output {target_path}'

    def make_cmd_package_request_github(self):
        url = self.opt_str('repo_url')
        target_path = self.opt_str('compressed_path')
        return f'curl -L -H "Accept: application/vnd.github+json" {url} --output {target_path}'

    def make_cmd_unpack_package(self):
        input_path = self.opt_str('compressed_path')
        output_dir = self.opt_str('target_hard_dir')
        if self.opt_str('package_kind') == 'tarball':
            return f'tar -xf {input_path} -C {output_dir} --strip-components=1'
        return ''

    def make_cmd_unlink_package(self):
        link_dir = self.opt_str('target_link_dir')
        return f'unlink {link_dir}'

    def make_cmd_softlink_package(self):
        src_dir = self.opt_str('target_hard_dir')
        link_dir = self.opt_str('target_link_dir')
        return f'ln -s {src_dir} {link_dir}'

    def do_step_download_package(self, action, depends_on):
        def act(cmd: str, target_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if not target_path.exists():
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, str(step_notes))

        cmd = self.make_cmd_package_request()

        target_path = Path(self.opt_str('compressed_path'))
        step = Step('download', depends_on, [], [target_path],
                    partial(act, cmd, target_path), cmd)
        action.set_step(step)
        return step

    def do_step_unlink_package(self, action, depends_on):
        def act(cmd: str, hard_path: Path, link_path:Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if link_path.exists() and str(link_path.resolve()) != str(hard_path):
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, str(step_notes))

        cmd = self.make_cmd_unlink_package()

        hard_path = Path(self.opt_str('target_hard_dir'))
        link_path = Path(self.opt_str('target_link_dir'))
        step = Step('unlink', depends_on, [link_path], [],
                    partial(act, cmd, hard_path, link_path), cmd)
        action.set_step(step)
        return step

    def do_step_unpack_package(self, action, depends_on):
        def act(cmd: str, src_path: Path, target_hard_dir: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if not src_path.exists():
                step_result = ResultCode.MISSING_INPUT
                step_notes = src_path
            else:
                if not target_hard_dir.exists() or not any(target_hard_dir.iterdir()):
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, str(step_notes))

        cmd = self.make_cmd_unpack_package()

        src_path = Path(self.opt_str('compressed_path'))
        target_hard_dir = Path(self.opt_str('target_hard_dir'))
        step = Step('unpack', depends_on, [], [target_hard_dir],
                    partial(act, cmd, src_path, target_hard_dir), cmd)
        action.set_step(step)
        return step

    def do_step_link_unpacked_project(self, action: Action, depends_on: Steps):
        def act(cmd: str, hard_dir: Path, link_dir: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if not hard_dir.exists():
                step_result = ResultCode.MISSING_INPUT
                step_notes = hard_dir
            else:
                if not link_dir.exists():
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, str(step_notes))

        cmd = self.make_cmd_softlink_package()

        target_hard_dir = Path(self.opt_str('target_hard_dir'))
        target_link_dir = Path(self.opt_str('target_link_dir'))
        step = Step('softlink', depends_on, [target_hard_dir], [target_link_dir],
                    partial(act, cmd, target_hard_dir, target_link_dir), cmd)
        action.set_step(step)
        return step

    def do_action_sync(self, action: Action):
        ''' Acquires the external dependency project. '''

        direc = self.opt_str('external_repos_anchor')
        hard_dir = self.opt_str('target_hard_dir')

        dir_dep = self.do_step_create_directory(action, None, Path(direc))
        dl_step = self.do_step_download_package(action, dir_dep)
        dir_package_step = self.do_step_create_directory(action, dl_step, Path(hard_dir))
        del_step = self.do_step_unlink_package(action, dir_package_step)
        unp_step = self.do_step_unpack_package(action, del_step)
        self.do_step_link_unpacked_project(action, unp_step)

    def do_action_clean(self, action: Action):
        pass
