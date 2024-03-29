''' This is the link phase in a multiphase buld.'''

from pathlib import Path

from ..action import Action, FileData
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

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output fies.'''

        archive_path = Path(self.opt_str('archive_path'))

        self.record_file_operation(
            None,
            FileData(archive_path.parent, 'dir', self),
            'create directory')

        prebuilt_objs = [FileData(prebuilt_obj_path, 'object', None)
                         for prebuilt_obj_path in self.get_all_prebuilt_obj_paths()]

        objs = self.get_dependency_output_files('object')
        objs.extend(prebuilt_objs)
        self.record_file_operation(
            objs,
            FileData(archive_path, 'static_library', self),
            'archive')

    def do_action_clean(self, action: Action):
        '''
        Cleans all object paths this phase builds.
        '''
        archive_path = self.get_archive_path()
        return self.do_step_delete_file(action, None, archive_path)

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        archive_path = self.get_archive_path()
        prefix = self.make_build_command_prefix()

        object_paths = [file_data.path for op in self.files.get_operations('archive')
                                       for file_data in op.input_files]

        step = self.do_step_create_directory(action, None, archive_path.parent)

        self.do_step_archive_objects_to_library(action, step,
            prefix, archive_path, object_paths)
