''' For fetching external dependency projects.'''

from pathlib import Path

from .options_owner import OptionsOwner
from .reporter import Reporter
from .utilities import do_shell_command, WorkingSet

class SyncExternalRepoClass(OptionsOwner):
    ''' Callable class (notably, not a phase) for fetching an external dependency project.'''
    def __init__(self, options: dict | None = None):
        super().__init__()
        project_root = str(WorkingSet.makefile_dir)
        self.options |= {
            'name': '',
            'repo_name': '',
            'package_version': '',
            # This is an anchor directory for external dependencies such as tarballs or 3rd party
            # repos.
            'ext_anchor': project_root,
            # Top-level external dependency packages directory.
            'ext_dir': 'external',
            'external_dependencies_anchor': '{ext_anchor}/{ext_dir}',
            'service': 'github',        # or gitlab, or some mercurial site, or www, ...
            'package_kind': 'tarball',
            'compression_kind': 'gzip',
            'tarball_extension': '.tar',
            'gzip_extension': '.gz',
            'package_extension': '{{package_kind}_extension}{{compression_kind}_extension}',
            'target_hard_dir': '{external_dependencies_anchor}/{name}-{package_version}',
            'target_link_dir': '{external_dependencies_anchor}/{name}',
            'compressed_file': '{name}-{package_version}{package_extension}',
            'compressed_path': '{external_dependencies_anchor}/{compressed_file}',

            'package_url': '{{service}_url}',
            'github_url': ('https://api.github.com/repos/{repo_name}'
                           '/tarball/{package_version}'),

            'pyke_makefiles': ['make.py'],
            'cmake_makefiles': ['cmakefilelistsdottext'],
            'make_makefiles': ['Makefile'],
        } | (options or {})
        self.reporter = Reporter(self)

    def make_cmd_create_external_directory(self, direc):
        ''' Return a cmd to make the externals anchor.'''
        needed = Path(direc).is_dir()
        return (f'mkdir -p {direc}', needed)

    def make_cmd_package_request(self, url, target_path):
        ''' Return a cmd to make the fetch command.'''
        if self.opt_str('service') == 'github':
            return self.make_cmd_package_request_github(url, target_path)
        needed = Path(target_path).is_file()
        return (f'curl -L {url} --output {target_path}', needed)

    def make_cmd_package_request_github(self, url, target_path):
        ''' Return a cmd to make the fetch command for github.'''
        needed = Path(target_path).is_file()
        return (f'curl -L -H "Accept: application/vnd.github+json" {url} --output {target_path}',
                needed)

    def make_cmd_create_repo_directory(self, direc):
        ''' Return a cmd to make the repo directory under the externals anchor.'''
        needed = Path(direc).is_dir()
        return (f'mkdir -p {direc}', needed)

    def make_cmd_unlink_softlink(self, hard_dir, link_dir):
        ''' Return a cmd to remove the repo softlink for a previous version.'''
        _link_dir = Path(link_dir)
        needed = not _link_dir.exists() or str(_link_dir.resolve()) == hard_dir
        return (f'unlink {link_dir}', needed)

    def make_cmd_unpack_package(self, compressed_path, hard_dir):
        ''' Return a cmd to unpack (probably unzip) a package (probably a tarball).'''
        _hard_dir = Path(hard_dir)
        needed = _hard_dir.is_dir() and any(_hard_dir.iterdir())
        if self.opt_str('package_kind') == 'tarball':
            return (f'tar -xf {compressed_path} -C {hard_dir} --strip-components=1', needed)
        return ('', needed)

    def make_cmd_softlink_package(self, hard_dir, link_dir):
        ''' Return a cmd to make a softlink to the unpacked repo.'''
        _link_dir = Path(link_dir)
        needed = _link_dir.exists() or _link_dir.resolve() == link_dir
        return (f'ln -s {hard_dir} {link_dir}', needed)

    def run_cmd(self, cmd, needed):
        ''' Run a command.'''
        if needed:
            print (f'\n{cmd}', end = '')
            res, _, err = do_shell_command(cmd)
            if res != 0:
                return (False, 'command failed', err)
            return (True, 'succeeded', '')
        return (True, 'already up to date', '')

    def create_external_directory(self):
        ''' Creates the externals anchor directory.'''
        direc = self.opt_str('external_dependencies_anchor')
        cmd, needed = self.make_cmd_create_external_directory(direc)
        self.reporter.report_step_start('create directory', [], [direc])
        succ, msg, notes = self.run_cmd(cmd, needed)
        self.reporter.report_step_end(cmd, succ, msg, notes)
        return succ

    def download_package(self):
        ''' Fetches the external repo.'''
        url = self.opt_str('package_url')
        target_path = self.opt_str('compressed_path')
        cmd, needed = self.make_cmd_package_request(url, target_path)
        self.reporter.report_step_start('download', [url], [target_path])
        succ, msg, notes = self.run_cmd(cmd, needed)
        self.reporter.report_step_end(cmd, succ, msg, notes)
        return succ

    def create_repo_directory(self):
        ''' Creates the versioned repo directory under the anchor.'''
        direc = self.opt_str('target_hard_dir')
        cmd, needed = self.make_cmd_create_repo_directory(direc)
        self.reporter.report_step_start('create directory', [], [direc])
        succ, msg, notes = self.run_cmd(cmd, needed)
        self.reporter.report_step_end(cmd, succ, msg, notes)
        return succ

    def unlink_softlink(self):
        ''' Removes any previously created softlink to a different version.'''
        hard_dir = self.opt_str('target_hard_dir')
        link_dir = self.opt_str('target_link_dir')
        cmd, needed = self.make_cmd_unlink_softlink(hard_dir, link_dir)
        self.reporter.report_step_start('unlink', [link_dir], [])
        succ, msg, notes = self.run_cmd(cmd, needed)
        self.reporter.report_step_end(cmd, succ, msg, notes)
        return succ

    def unpack_package(self):
        ''' Uncompress and unpack the downloaded repo.'''
        compressed_path = self.opt_str('compressed_path')
        hard_dir = self.opt_str('target_hard_dir')
        cmd, needed = self.make_cmd_unpack_package(compressed_path, hard_dir)
        self.reporter.report_step_start('unpack', [compressed_path], [hard_dir])
        succ, msg, notes = self.run_cmd(cmd, needed)
        self.reporter.report_step_end(cmd, succ, msg, notes)
        return succ

    def link_unpacked_project(self):
        ''' Creates a softlink for the versioned repo.'''
        hard_dir = self.opt_str('target_hard_dir')
        link_dir = self.opt_str('target_link_dir')
        cmd, needed = self.make_cmd_softlink_package(hard_dir, link_dir)
        self.reporter.report_step_start('link', [hard_dir], [link_dir])
        succ, msg, notes = self.run_cmd(cmd, needed)
        self.reporter.report_step_end(cmd, succ, msg, notes)
        return succ

    def fetch(self):
        ''' Fetch commands.'''
        succ = True
        self.reporter.report_action_phase_start('sync', '', '')
        succ = succ and self.create_external_directory()
        succ = succ and self.download_package()
        succ = succ and self.create_repo_directory()
        succ = succ and self.unlink_softlink()
        succ = succ and self.unpack_package()
        succ = succ and self.link_unpacked_project()
        self.reporter.report_action_phase_end(succ)
        return self.opt_str('target_link_dir')

def sync_external_repo(options: dict | None = None):
    ''' Fetches the repo.'''
    syncer = SyncExternalRepoClass(options)
    return syncer.fetch()
