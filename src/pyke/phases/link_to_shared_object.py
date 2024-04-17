''' Links objects to a shared object.'''

from pathlib import Path

from ..action import Action, FileData
from .c_family_build import CFamilyBuildPhase

class LinkToSharedObjectPhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(None, dependencies)
        self.options |= {
            'name': 'link_to_shared_object',
            'target_path': '{shared_object_path}',
        }
        self.options |= (options or {})

    def patch_options(self):
        ''' Fixups run before file operations.'''
        for dep in self.enumerate_dependencies():
            dep.push_opts({'relocatable_code': True}, True, True)

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output files.'''

        so_path = Path(self.opt_str('shared_object_path'))

        self.record_file_operation(
            None,
            FileData(so_path.parent, 'dir', self),
            'create directory')

        prebuilt_objs = [FileData(prebuilt_obj_path, 'object', None)
                         for prebuilt_obj_path in self.get_all_prebuilt_obj_paths()]

        objs = self.get_direct_dependency_output_files('object')
        objs.extend(prebuilt_objs)
        self.record_file_operation(
            objs,
            FileData(so_path, 'shared_object', self),
            'link to shared object')

        if self.opt_bool('generate_versioned_sonames'):
            anchor = Path(self.opt_str('shared_object_anchor'))
            soname = anchor / Path(self.opt_str("posix_so_soname"))
            linkername = anchor / Path(self.opt_str("posix_so_linker_name"))
            self.record_file_operation(
                FileData(so_path, 'shared_object', self),
                FileData(soname, 'soft_link', self),
                'generate soft links')
            self.record_file_operation(
                FileData(soname, 'soft_link', self),
                FileData(linkername, 'soft_link', self),
                'generate soft links')

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        so_path = Path(self.opt_str('shared_object_path'))
        object_paths = [file.path for op in self.files.get_operations('link to shared object')
                                  for file in op.input_files if file.file_type == 'object']

        step = self.do_step_create_directory(action, None, so_path.parent)

        step = self.do_step_link_objects_to_shared_object(action, step,
            object_paths, so_path)
        if self.opt_bool('generate_versioned_sonames'):
            step = self.do_step_softlink_soname_to_real_name(action, step)
            step = self.do_step_softlink_linker_name_to_soname(action, step)
