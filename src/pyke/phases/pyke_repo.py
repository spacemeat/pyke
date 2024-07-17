''' This phase syncs an external repository to a specific version. '''

from functools import partial
from pathlib import Path
from typing import TypeAlias

from .phase import Phase
from ..action import Action, Step, Result, ResultCode
from ..utilities import do_shell_command, PykeMakefileNotFoundError, PykeMakefileNotLoadedError
from ..pyke import PykeExecutor, ReturnCode

Steps: TypeAlias = list[Step] | Step | None

class PykeRepoPhase(Phase):
    '''
    Phase class for syncing a remote repository.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(None, dependencies)
        self.options |= {
            'name': '',
            'makefile': '',
            'makefile_path': '{project_anchor}/{makefile}',
            'use_deps': [],
        }
        self.options |= (options or {})
        self.executor: PykeExecutor | None = None

    def compute_file_operations(self):
        ''' Clone the file operations in all dependencies, since this is basically a pass-through 
        phase. '''
        for dep in self.dependencies:
            for file_op in dep.files.operations:
                self.files.record(file_op)

    def cache_pyke_executor(self):
        ''' Loads the pyke makefile, and hooks the specified dependencies up. This may fail if
        the pyke repo is not yet downloaded (see ExternalRepoPhase); later actions may allow
        this to succeed.'''
        if not self.executor:
            pyke_makefile_path = self.opt_str('makefile_path')
            pyke_fds = self.get_direct_dependency_output_files('pyke_makefile')
            if len(pyke_fds) > 0:
                pyke_makefile_path = pyke_fds[0].path

            self.executor = PykeExecutor(pyke_makefile_path)
            root = None
            try:
                root = self.executor.load()
            except PykeMakefileNotFoundError:
                return ReturnCode.MAKEFILE_NOT_FOUND

            except PykeMakefileNotLoadedError:
                return ReturnCode.MAKEFILE_DID_NOT_LOAD

            for phase_name in self.opt_list('use_deps'):
                phase = root.find_dep(phase_name)
                if phase:
                    # What a dumb workaround.
                    # It's because Self, used in Phase, gets promoted to PykeRepoPhase. >:(
                    ph: Phase = self
                    ph.depend_on(phase)

            self.files.operations = []
            self.compute_file_operations_in_dependencies()

        return ReturnCode.SUCCEEDED

    def do(self, action: Action):
        ''' Overrides Phase.do() to swing actions to the deferred pyke phases.'''
        # make the PykeExecutor if we can
        self.cache_pyke_executor()
        # Even if we couldn't, we can still invoke actions like sync. Further actions will
        # try again to make the executor, and if they work, actions like build will propagate.
        super().do(action)
