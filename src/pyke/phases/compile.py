''' This is the compile phase of a multi-phase build.'''

from ..action import Action, ResultCode, FileData
from .c_family_build import CFamilyBuildPhase

class CompilePhase(CFamilyBuildPhase):
    '''
    Phase class for building C/C++ files to objects.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = {
            'build_operation': 'compile_to_object',
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

    def do_action_build(self, action: Action):
        '''
        Builds all objects.
        '''
        prefix = self.make_build_command_prefix()
        args = self.make_compile_arguments()

        dirs = {}
        all_dirs = [fd.path for fd in self.files.get_output_files('dir')]
        for direc in list(dict.fromkeys(all_dirs)):
            dirs[direc] = self.do_step_create_directory(action, None, direc)

        for file_op in self.files.get_operations('compile'):
            for src, obj in zip(file_op.input_files, file_op.output_files):
                self.do_step_compile_src_to_object(
                    action, dirs[obj.path.parent], prefix, args, src.path, obj.path)
