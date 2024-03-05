''' This is the compile phase of a multi-phase build.'''

from ..action import ActionResult
from .c_family_build import CFamilyBuildPhase

class CompilePhase(CFamilyBuildPhase):
    '''
    Phase class for building C/C++ files to objects.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'name': 'compile',
        } | options | {
            'build_operation': 'compile_to_object',
        }
        super().__init__(options, dependencies)
        self.default_action = 'build'

    def do_action_clean(self):
        '''
        Cleans all object paths this phase builds.
        '''
        step_results = []
        for _, obj_path in self.get_all_src_and_object_paths():
            step_results.append(self.do_step_delete_file(obj_path))

        return ActionResult('clean', tuple(step_results))

    def do_action_build(self):
        '''
        Builds all object paths.
        '''
        step_results = []
        prefix = self.make_build_command_prefix()
        args = self.make_compile_arguments()

        for src_path, obj_path in self.get_all_src_and_object_paths():
            step_results.append(self.do_step_create_directory(obj_path.parent))

            if bool(step_results[-1]):
                step_results.append(self.do_step_compile_src_to_object(
                    prefix, args, src_path, obj_path))

        return ActionResult('build', tuple(step_results))


