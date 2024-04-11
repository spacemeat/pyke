
''' Contains the ProjectPhase phase class. '''

from ..action import Action
from .phase import Phase

class ProjectPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = options or {}
        super().__init__(options, dependencies)
        self.is_project_phase = True
        self.override_project_dependency_options = True
