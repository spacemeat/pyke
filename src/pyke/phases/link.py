''' This is the link phase in a multiphase buld.'''

from pathlib import Path

from ..action import Action, FileData
from .c_family_build import CFamilyBuildPhase

class LinkPhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = {
            'name': 'link',
            'build_operation': 'link_to_executable',
        } | (options or {})
        super().__init__(options, dependencies)

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output fies.'''

        exe_path = Path(self.opt_str('exe_path'))

        self.record_file_operation(
            None,
            FileData(exe_path.parent, 'dir', self),
            'create directory')

        prebuilt_objs = [FileData(prebuilt_obj_path, 'object', None)
                         for prebuilt_obj_path in self.get_all_prebuilt_obj_paths()]

        objs = self.get_dependency_output_files('object')
        objs.extend(prebuilt_objs)
        self.record_file_operation(
            objs,
            FileData(exe_path, 'executable', self),
            'link')

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        exe_path = self.get_exe_path()

        prefix = self.make_build_command_prefix()
        args = self.make_link_arguments()

        object_paths = [file_data.path for op in self.files.get_operations('link')
                                       for file_data in op.input_files]

        step = self.do_step_create_directory(action, None, exe_path.parent)

        self.do_step_link_objects_to_exe(action, step,
            prefix, args, exe_path, object_paths)
