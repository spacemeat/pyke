''' This is the link phase in a multiphase buld.'''

from pathlib import Path

from ..action import Action, FileData
from .c_family_build import CFamilyBuildPhase
from ..options import OptionOp
from ..utilities import uniquify_list

class LinkToExePhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = {
            'name': 'link',
            'target_path': '{exe_path}',
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

        objs = self.get_direct_dependency_output_files('object')
        objs.extend(prebuilt_objs)
        self.record_file_operation(
            objs,
            FileData(exe_path, 'executable', self),
            'link')

    def patch_options_post_files(self):
        ''' Fixup options after file operations.'''
        archive_objs = self.get_direct_dependency_output_files('archive')
        shared_objs = self.get_direct_dependency_output_files('shared_object')
        # fill in lib_dirs
        new_dirs = [ *[str(file.path.parent) for file in archive_objs],
                     *[str(file.path.parent) for file in shared_objs] ]
        self.push_opts({'lib_dirs': (OptionOp.EXTEND, uniquify_list(new_dirs),
            )})
        # fill in rpath
        if not self.opt_bool('build_for_deployment'):
            self.push_opts({'rpath': ({ str(file.path.parent): True for file in shared_objs })})
        # fill in libs
        self.push_opts({'libs':
            ({file.generating_phase.opt_str('archive_basename'): 'archive'
                        for file in archive_objs})})
        self.push_opts({'libs':
            ({file.generating_phase.opt_str('shared_object_basename'): 'shared_object'
                        for file in shared_objs})})

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
