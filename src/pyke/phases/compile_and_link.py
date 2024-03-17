''' This is the compile-and-link phase for single-phase build.'''

from ..action import ActionResult
from .c_family_build import CFamilyBuildPhase

from ..utilities import WorkingSet

class CompileAndLinkPhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options, dependencies = None):
        options = {
            'name': 'compile_and_link',
            'build_operation': 'compile_to_executable',
        } | options
        super().__init__(options, dependencies)

    def do_action_clean(self):
        '''
        Cleans all object paths this phase builds.
        '''
        exe_path = self.get_exe_path()

        step_results = []

        if self.opt_bool('incremental_build'):
            for _, obj_path in self.get_all_src_and_object_paths():
                step_results.append(self.do_step_delete_file(obj_path))

        step_results.append(self.do_step_delete_file(exe_path))

        return ActionResult('clean', tuple(step_results))

    def do_action_build(self):
        '''
        Builds all object paths.
        '''
        step_results = []
        exe_path = self.get_exe_path()

        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()
        l_args = self.make_link_arguments()

        if self.opt_bool('incremental_build'):
            for src_path, obj_path in self.get_all_src_and_object_paths():
                step_results.append(self.do_step_create_directory(obj_path.parent))

                if bool(step_results[-1]):
                    step_results.append(self.do_step_compile_src_to_object(
                        prefix, c_args, src_path, obj_path))

            if all((bool(res) for res in step_results)):
                object_paths = self.get_all_object_paths()

                step_results.append(self.do_step_create_directory(exe_path.parent))
                if bool(step_results[-1]):
                    step_results.append(self.do_step_link_objects_to_exe(
                        prefix, l_args, exe_path, object_paths))
        else:
            src_paths = self.get_all_src_paths()

            step_results.append(self.do_step_create_directory(exe_path.parent))
            if bool(step_results[-1]):
                step_results.append(self.do_step_compile_srcs_to_exe(
                    prefix, c_args | l_args, src_paths, exe_path))

        return ActionResult('build', tuple(step_results))
