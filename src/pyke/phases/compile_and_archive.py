''' This is the compile-and-link phase for single-phase build.'''

from pathlib import Path

from ..action import Action, ResultCode, FileData
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

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output fies.'''
        for src_file_data in self.get_dependency_output_files('source'):
            obj_path = self.make_obj_path_from_src(src_file_data.path)
            self.record_file_operation(
                None,
                FileData(obj_path.parent, 'dir', self),
                'create directory')
            self.record_file_operation(
                src_file_data,
                FileData(obj_path, 'object', self),
                'compile')

        for src_path in self.get_all_src_paths():
            obj_path = self.make_obj_path_from_src(src_path)
            self.record_file_operation(
                None,
                FileData(obj_path.parent, 'dir', self),
                'create directory')
            self.record_file_operation(
                FileData(src_path, 'source', None),
                FileData(obj_path, 'object', self),
                'compile')

        self.record_file_operation(
            None,
            FileData(Path(self.opt_str('archive_path')).parent, 'dir', self),
            'create directory')

        objs = self.get_dependency_output_files('object')
        objs.extend(self.files.get_output_files('object'))
        self.record_file_operation(
            objs,
            FileData(Path(self.opt_str('archive_path')), 'archive', self),
            'archive')

    def do_action_clean(self, action: Action):
        '''
        Cleans all object paths this phase builds.
        '''
        archive_path = self.get_archive_path()

        for obj in self.files.get_output_files('object'):
            self.do_step_delete_file(obj.path, action)

        self.do_step_delete_file(archive_path, action)

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        archive_path = self.get_archive_path()

        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()

        for direc in list(dict.fromkeys(self.files.get_output_files('dir'))):
            self.do_step_create_directory(direc, action)

        for src, obj in zip(self.files.get_operations('compile')):
            self.do_step_compile_src_to_object(prefix, c_args, src.path, obj.path, action)

        prefix = self.make_archive_command_prefix()
        object_paths = list(obj for obj in self.files.get_output_files('object'))

        self.do_step_create_directory(archive_path.parent, action)
        self.do_step_archive_objects_to_library(
            prefix, archive_path, object_paths, action)
