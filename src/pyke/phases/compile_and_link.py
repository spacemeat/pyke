''' This is the compile-and-link phase for single-phase build.'''

from pathlib import Path

from ..action import Action, FileData
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
                include_files = [FileData(path, 'header', None) for path in
                    self.get_includes_src_to_object(src.path, obj_path)]
                self.record_file_operation(
                    None,
                    FileData(obj_path.parent, 'dir', self),
                    'create directory')
                self.record_file_operation(
                    [src, *include_files],
                    FileData(obj_path, 'object', self),
                    'compile')

            for src_path in self.get_all_src_paths():
                obj_path = self.make_obj_path_from_src(src_path)
                include_files = [FileData(path, 'header', None) for path in
                    self.get_includes_src_to_object(src_path, obj_path)]
                self.record_file_operation(
                    None,
                    FileData(obj_path.parent, 'dir', self),
                    'create directory')
                self.record_file_operation(
                    [FileData(src_path, 'source', None), *include_files],
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
            src_paths = self.get_all_src_paths()
            for src_path in src_paths:
                srcs.append(FileData(src_path, 'source', None))
            include_files = [FileData(path, 'header', None) for path in
                self.get_includes_srcs_to_exe(src_paths, obj_path)]
            self.record_file_operation(
                [*srcs, *include_files],
                FileData(exe_path, 'executable', self),
                'compile and link')

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        exe_path = self.get_exe_path()

        dirs = {}
        all_dirs = [fd.path for fd in self.files.get_output_files('dir')]
        for direc in list(dict.fromkeys(all_dirs)):
            dirs[direc] = self.do_step_create_directory(action, None, direc)

        if self.opt_bool('incremental_build'):
            compile_steps = []
            for file_op in self.files.get_operations('compile'):
                deps = file_op.input_files
                obj = file_op.output_files[0]
                src = None
                inc_paths = []
                for dep in deps:
                    if dep.file_type == 'source':
                        src = dep
                    else:
                        inc_paths.append(dep.path)
                compile_steps.append(
                    self.do_step_compile_src_to_object(action, dirs[obj.path.parent],
                        src.path, inc_paths, obj.path))

            object_paths = [src.path
                for file_op in self.files.get_operations('link')
                for src in file_op.input_files]

            self.do_step_link_objects_to_exe(action, [*compile_steps, dirs[exe_path.parent]],
                object_paths, exe_path)
        else:
            src_paths = [src.path for src in self.files.get_input_files('source')]
            inc_paths = [src.path for src in self.files.get_input_files('header')]

            self.do_step_compile_srcs_to_exe(action, dirs[exe_path.parent],
                src_paths, inc_paths, exe_path)
