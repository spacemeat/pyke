
''' Contains the ProjectPhase phase class. '''

from .phase import Phase
from ..utilities import WorkingSet

class ProjectPhase(Phase):
    '''
    Intermediate class to handle making command lines for various toolkits.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'name': 'pyke',
            'build_operation': 'project',
        } | options
        super().__init__(options, dependencies)
        self.default_action = 'build'
        self.override_project_dependency_options = True
        WorkingSet.using_phases.append(self)
