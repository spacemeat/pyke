''' This is the compile-and-link phase for single-phase build.'''

from ..action import Action, ResultCode
from .c_family_build import CFamilyBuildPhase

class CompileAndArchivePhase(CFamilyBuildPhase):
    '''
    Phase class for building and archiving object files to a static library archive.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = {
            'build_operation': 'compile_to_archive',
        } | (options or {})
        super().__init__(options, dependencies)

    def do_action_clean(self, action: Action):
        '''
        Cleans all object paths this phase builds.
        '''
        archive_path = self.get_archive_path()

        res = ResultCode.SUCCEEDED
        for _, obj_path in self.get_all_src_and_object_paths():
            res = res if res.failed() else self.do_step_delete_file(obj_path, action)

        res = res if res.failed() else self.do_step_delete_file(archive_path, action)

        return res

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        archive_path = self.get_archive_path()

        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()

        res = ResultCode.SUCCEEDED
        for src_path, obj_path in self.get_all_src_and_object_paths():
            res = res if res.failed() else self.do_step_create_directory(
                obj_path.parent, action)
            res = res if res.failed() else self.do_step_compile_src_to_object(
                prefix, c_args, src_path, obj_path, action)

        if res.succeeded():
            prefix = self.make_archive_command_prefix()
            object_paths = self.get_all_object_paths()

            res = res if res.failed() else self.do_step_create_directory(
                archive_path.parent, action)
            res = res if res.failed() else self.do_step_archive_objects_to_library(
                prefix, archive_path, object_paths, action)

        return res
