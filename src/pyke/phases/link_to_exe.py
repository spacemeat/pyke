''' This is the link phase in a multiphase buld.'''

from pathlib import Path

from ..action import Action, FileData
from .c_family_build import CFamilyBuildPhase

class LinkToExePhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(None, dependencies)
        self.options |= {
            'name': 'link_to_exe',
            'target_path': '{exe_path}',
        }
        self.options |= (options or {})

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output files.'''

        exe_path = Path(self.opt_str('exe_path'))

        self.record_file_operation(
            None,
            FileData(exe_path.parent, 'dir', self),
            'create directory')

        prebuilt_objs = [FileData(prebuilt_obj_path, 'object', None)
                         for prebuilt_obj_path in self.get_all_prebuilt_obj_paths()]

        objs = self.get_direct_dependency_output_files('object')
        objs.extend(self.get_direct_dependency_output_files('archive'))
        objs.extend(self.get_direct_dependency_output_files('shared_object'))
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
        object_paths = [file.path for op in self.files.get_operations('link')
                                  for file in op.input_files if file.file_type == 'object']

        step = self.do_step_create_directory(action, None, exe_path.parent)

        self.do_step_link_objects_to_exe(action, step,
            object_paths, exe_path)

    def do_action_run(self, action: Action):
        ''' Runs the executable in a new shell.'''
        exe_path = self.get_exe_path()
        self.do_step_run_executable(action, None, exe_path)
