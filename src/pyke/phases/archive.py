''' This is the link phase in a multiphase buld.'''

from ..action import Action
from .c_family_build import CFamilyBuildPhase

class ArchivePhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = {
            'name': 'archive',
            'build_operation': 'archive_to_library',
        } | (options or {})
        super().__init__(options, dependencies)

    def get_all_object_paths(self):
        '''
        Gets the object file paths from each dependency.
        '''
        for dep in self.dependencies:
            yield from dep.get_all_object_paths()

    def do_action_clean(self, action: Action):
        '''
        Cleans all object paths this phase builds.
        '''
        archive_path = self.get_archive_path()
        return self.do_step_delete_file(archive_path, action)

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        object_paths = self.get_all_object_paths()
        archive_path = self.get_archive_path()

        prefix = self.make_build_command_prefix()

        res = self.do_step_create_directory(archive_path.parent, action)
        res = res if res.failed() else self.do_step_archive_objects_to_library(
            prefix, archive_path, object_paths, action)

        return res
