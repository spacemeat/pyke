''' This is the link phase in a multiphase buld.'''

from ..action import Action
from .c_family_build import CFamilyBuildPhase

class LinkPhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'name': 'link',
            'build_operation': 'link_to_executable',
        } | options
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
        exe_path = self.get_exe_path()
        return self.do_step_delete_file(exe_path, action)

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        object_paths = self.get_all_object_paths()
        exe_path = self.get_exe_path()

        prefix = self.make_build_command_prefix()
        args = self.make_link_arguments()

        res = self.do_step_create_directory(exe_path.parent, action)
        res = res.failed() or self.do_step_link_objects_to_exe(
            prefix, args, exe_path, object_paths, action)

        return res
