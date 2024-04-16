
''' Contains the ProjectPhase phase class. '''

from .phase import Phase

class ProjectPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(None, dependencies)
        self.options |= (options or {})
        self.is_project_phase = True
