''' This is the compile-and-link phase for single-phase build.'''

from ..action import Action, ResultCode
from .c_family_build import CFamilyBuildPhase

class CompileAndLinkPhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, name: str | None = None, options: dict | None = None, dependencies = None):
        options = {
            'build_operation': 'compile_to_executable',
        } | (options or {})
        super().__init__(name, options, dependencies)

    def do_action_clean(self, action: Action):
        '''
        Cleans all object paths this phase builds.
        '''
        exe_path = self.get_exe_path()

        res = ResultCode.SUCCEEDED
        if self.opt_bool('incremental_build'):
            for _, obj_path in self.get_all_src_and_object_paths():
                res = res if res.failed() else self.do_step_delete_file(obj_path, action)

        res = res if res.failed() else self.do_step_delete_file(exe_path, action)

        return res

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        exe_path = self.get_exe_path()

        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()
        l_args = self.make_link_arguments()

        res = ResultCode.SUCCEEDED
        if self.opt_bool('incremental_build'):
            for src_path, obj_path in self.get_all_src_and_object_paths():
                res = res if res.failed() else self.do_step_create_directory(
                    obj_path.parent, action)
                res = res if res.failed() else self.do_step_compile_src_to_object(
                    prefix, c_args, src_path, obj_path, action)

            if res.succeeded():
                object_paths = self.get_all_object_paths()

                res = res if res.failed() else self.do_step_create_directory(
                    exe_path.parent, action)
                res = res if res.failed() else self.do_step_link_objects_to_exe(
                    prefix, l_args, exe_path, object_paths, action)
        else:
            src_paths = self.get_all_src_paths()

            res = res if res.failed() else self.do_step_create_directory(exe_path.parent, action)
            res = res if res.failed() else self.do_step_compile_srcs_to_exe(
                prefix, c_args | l_args, src_paths, exe_path, action)

        return res
