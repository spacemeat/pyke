''' This is the compile-and-link phase for single-phase build.'''

from pathlib import Path

from ..action import Action, FileData
from .c_family_build import CFamilyBuildPhase

class CompileAndLinkToSharedObjectPhase(CFamilyBuildPhase):
    '''
    Phase class for linking object files to build executable binaries.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(None, dependencies)
        self.options |= {
            'name': 'compile_and_link_to_shared_object',
            'target_path': '{shared_object_path}',
            'relocatable_code': True,
        }
        self.options |= (options or {})

    def patch_options(self):
        ''' Fixups run before file operations.'''
        super().patch_options()
        for dep in self.iterate_dep_tree():
            dep.push_opts({'relocatable_code': True}, True, True)

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output files.'''
        so_path = Path(self.opt_str('shared_object_path'))

        prebuilt_objs = [FileData(prebuilt_obj_path, 'object', None)
                         for prebuilt_obj_path in self.get_all_prebuilt_obj_paths()]

        for src in self.get_direct_dependency_output_files('source'):
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
            FileData(so_path.parent, 'dir', self),
            'create directory')

        objs = self.get_direct_dependency_output_files('object')
        objs.extend(self.get_direct_dependency_output_files('archive'))
        objs.extend(self.get_direct_dependency_output_files('shared_object'))
        objs.extend(self.files.get_output_files('object'))
        objs.extend(prebuilt_objs)
        self.record_file_operation(
            objs,
            FileData(so_path, 'shared_object', self),
            'link to shared object')

    def do_action_build(self, action: Action):
        '''
        Builds all object paths.
        '''
        so_path = Path(self.opt_str('shared_object_path'))

        dirs = {}
        all_dirs = [fd.path for fd in self.files.get_output_files('dir')]
        for direc in list(dict.fromkeys(all_dirs)):
            dirs[direc] = self.do_step_create_directory(action, None, direc)

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
            if src:
                compile_steps.append(
                    self.do_step_compile_src_to_object(action, dirs[obj.path.parent],
                        src.path, inc_paths, obj.path))

        object_paths = [src.path
            for file_op in self.files.get_operations('link to shared object')
            for src in file_op.input_files if src.file_type == 'object']

        self.do_step_link_objects_to_shared_object(
            action, [*compile_steps, dirs[so_path.parent]],
            object_paths, so_path)
