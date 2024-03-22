''' This is the compile phase of a multi-phase build.'''

from pathlib import Path
from ..action import Action, ResultCode
from .c_family_build import CFamilyBuildPhase

class CompilePhase(CFamilyBuildPhase):
    '''
    Phase class for building C/C++ files to objects.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'name': 'compile',
            'build_operation': 'compile_to_object',
        } | options
        super().__init__(options, dependencies)

    def do_action_clean(self, action: Action):
        '''
        Cleans all object paths this phase builds.
        '''
        res = ResultCode.SUCCEEDED
        for _, obj_path in self.get_all_src_and_object_paths():
            res = res if res.failed() else self.do_step_delete_file(obj_path, action)
        return res

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        prefix = self.make_build_command_prefix()
        args = self.make_compile_arguments()

        res = ResultCode.SUCCEEDED
        for src_path, obj_path in self.get_all_src_and_object_paths():
            res = res if res.failed() else self.do_step_create_directory(obj_path.parent, action)
            res = res if res.failed() else self.do_step_compile_src_to_object(
                prefix, args, src_path, obj_path, action)
        return res
