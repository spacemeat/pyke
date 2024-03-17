
''' Contains the ProjectPhase phase class. '''

from .phase import Phase

class ProjectPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'name': 'pyke',
        } | options
        super().__init__(options, dependencies)
        self.is_project_phase = True
        self.default_action = 'build'
        self.override_project_dependency_options = True

    def push_opts(self, overrides: dict,
                  include_deps: bool = True, include_project_deps: bool = False):
        '''
        Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line.
        '''
        super().push_opts(overrides, include_deps, include_project_deps)

    def pop_opts(self, keys: list[str],
                 include_deps: bool = True, include_project_deps: bool = False):
        '''
        Removes pushed option overrides.
        '''
        super().pop_opts(keys, include_deps, include_project_deps)

