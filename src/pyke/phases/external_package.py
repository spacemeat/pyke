''' This phase syncs an external repository to a specific version. '''

from functools import partial
from pathlib import Path
from typing import TypeAlias

from ..action import Action, Step, Result, ResultCode
from ..utilities import do_shell_command
from .phase import Phase

Steps: TypeAlias = list[Step] | Step | None

class ExternalPackagePhase(Phase):
    '''
    Phase class for syncing a remote repository.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(None, dependencies)
        self.options |= {
            'name': 'external_get',
            'project_name': '',
            'repo_project_name': '',
            'package_version': '',
            'service': 'github',        # or gitlab, or some mercurial site, or www, ...
            'package_kind': 'tarball',
            'compression_kind': 'gzip',
            'tarball_extension': '.tar',
            'gzip_extension': '.gz',
            'package_extension': '{{package_kind}_extension}{{compression_kind}_extension}',
            'target_hard_dir': '{external_dependencies_anchor}/{project_name}-{package_version}',
            'target_link_dir': '{external_dependencies_anchor}/{project_name}',
            'compressed_file': '{project_name}-{package_version}{package_extension}',
            'compressed_path': '{external_dependencies_anchor}/{compressed_file}',

            'package_url': '{{service}_url}',
            'github_url': ('https://api.github.com/repos/{repo_project_name}'
                           '/tarball/{package_version}'),
        }
        self.options |= (options or {})

    def make_package_url(self):
        return self.opt_str('package_url')

    def make_cmd_package_request(self):
        if self.opt_str('service') == 'github':
            return self.make_cmd_package_request_github()

        url = self.opt_str('package_url')
        target_path = self.opt_str('compressed_path')
        return f'curl -L {url} --output {target_path}'

    def make_cmd_package_request_github(self):
        url = self.opt_str('package_url')
        target_path = self.opt_str('compressed_path')
        return f'curl -L -H "Accept: application/vnd.github+json" {url} --output {target_path}'

    def make_cmd_unpack_package(self):
        input_path = self.opt_str('compressed_path')
        output_dir = self.opt_str('target_hard_dir')
        if self.opt_str('package_kind') == 'tarball':
            return f'tar -xf {input_path} -C {output_dir} --strip-components=1'
        return ''

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
                if not link_dir.exists() or link_dir.resolve != hard_dir:
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
        step = Step('link', depends_on, [target_hard_dir], [target_link_dir],
                    partial(act, cmd, target_hard_dir, target_link_dir), cmd)
        action.set_step(step)
        return step

    def do_action_sync(self, action: Action):
        ''' Acquires the external dependency project. '''

        direc = self.opt_str('external_dependencies_anchor')
        hard_dir = self.opt_str('target_hard_dir')
        link_dir = self.opt_str('target_link_dir')

        dir_dep = self.do_step_create_directory(action, None, Path(direc))
        dl_step = self.do_step_download_package(action, dir_dep)
        dir_package_step = self.do_step_create_directory(action, dl_step, Path(hard_dir))
        del_step = self.do_step_delete_file(action, dir_package_step, Path(link_dir))
        unp_step = self.do_step_unpack_package(action, del_step)
        self.do_step_link_unpacked_project(action, unp_step)
