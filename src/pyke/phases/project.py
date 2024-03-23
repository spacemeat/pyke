
''' Contains the ProjectPhase phase class. '''

from .phase import Phase

class ProjectPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, name: str | None = None, options: dict | None = None, dependencies = None):
        options = {
            'name': 'pyke',
        } | (options or {})
        super().__init__(name, options, dependencies)
        self.is_project_phase = True
        self.phase_names = {}
        self.override_project_dependency_options = True

    def uniquify_phase_names(self):
        ''' Updates phase names within an owning project phase to be unique.'''
        phases = [phase for phase in self.enumerate_dependencies() if not phase.is_project_phase]
        for phase in phases:
            name = phase.name
            if name:
                if name not in self.phase_names:
                    phase.name = name
                    self.phase_names[name] = phase
                    return
            else:
                name = f'{type(phase).__name__}'

            ordinal = 0
            oname = f'{name}_{ordinal}'
            while oname in self.phase_names:
                ordinal += 1
                oname = f'{name}_{ordinal}'
            phase.name = name
            self.phase_names[name] = phase

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

