
''' Contains the ProjectPhase phase class. '''

from ..action import Action, ResultCode
from .phase import Phase

class ProjectPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = options or {}
        super().__init__(options, dependencies)
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

    def do(self, action: Action):
        '''
        Performs an action, such as 'build' or 'run'. 
        '''
        for dep in self.dependencies:
            if dep.is_project_phase:
                dep.do(action)

        if action.set_project(self) != ResultCode.NOT_YET_RUN:
            return

        super().do(action)
