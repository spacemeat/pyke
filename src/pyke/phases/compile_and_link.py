''' This is the compile-and-link phase for single-phase build.'''

from pathlib import Path

from ..action import Action, ResultCode, FileData
from .c_family_build import CFamilyBuildPhase

class CompileAndLinkPhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        options = {
            'build_operation': 'compile_to_executable',
        } | (options or {})
        super().__init__(options, dependencies)

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output fies.'''

        exe_path = Path(self.opt_str('exe_path'))

        prebuilt_objs = [FileData(prebuilt_obj_path, 'object', None)
                         for prebuilt_obj_path in self.get_all_prebuilt_obj_paths()]
        if len(prebuilt_objs) and self.opt_bool('incremental_build') == False > 0:
            self.push_opts({'incremental_build': True})

        if self.opt_bool('incremental_build'):
            for src in self.get_dependency_output_files('source'):
                obj_path = self.make_obj_path_from_src(src.path)
                self.record_file_operation(
                    None,
                    FileData(obj_path.parent, 'dir', self),
                    'create directory')
                self.record_file_operation(
                    src,
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
                FileData(exe_path.parent, 'dir', self),
                'create directory')

            objs = self.get_dependency_output_files('object')
            objs.extend(self.files.get_output_files('object'))
            objs.extend(prebuilt_objs)
            self.record_file_operation(
                objs,
                FileData(exe_path, 'executable', self),
                'link')

        else:
            self.record_file_operation(
                None,
                FileData(exe_path.parent, 'dir', self),
                'create directory')

            srcs = self.get_dependency_output_files('source')
            for src_path in self.get_all_src_paths():
                srcs.append(FileData(src_path, 'source', None))
            self.record_file_operation(
                srcs,
                FileData(exe_path, 'executable', self),
                'compile and link')

    def do_action_clean(self, action: Action):
        '''
        Cleans all object paths this phase builds.
        '''
        exe_path = self.get_exe_path()

        for obj in self.files.get_output_files('object'):
            self.do_step_delete_file(action, None, obj.path)

        self.do_step_delete_file(action, None, exe_path)

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        exe_path = self.get_exe_path()

        prefix = self.make_build_command_prefix()
        c_args = self.make_compile_arguments()
        l_args = self.make_link_arguments()

        dirs = {}
        for direc in list(dict.fromkeys(self.files.get_output_files('dir'))):
            dirs[direc] = self.do_step_create_directory(direc, None, action)

        if self.opt_bool('incremental_build'):
            compile_steps = []
            for src, obj in zip(self.files.get_operations('compile')):
                compile_steps.append(self.do_step_compile_src_to_object(action, dirs[obj.path],
                                prefix, c_args, src.path, obj.path))

            object_paths = list(obj for obj in self.files.get_output_files('object'))

            self.do_step_link_objects_to_exe(action, [*compile_steps, dirs[exe_path]],
                prefix, l_args, exe_path, object_paths)
        else:
            src_paths = self.files.get_input_files('source')

            self.do_step_compile_srcs_to_exe(action, dirs[exe_path],
                prefix, c_args | l_args, src_paths, exe_path)
