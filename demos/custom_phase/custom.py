''' Custom phase for pyke project.'''

from functools import partial
from pathlib import Path
from pyke import (CFamilyBuildPhase, Action, ResultCode, Step, Result, FileData,
                  input_path_is_newer, do_shell_command)

class ContrivedCodeGenPhase(CFamilyBuildPhase):
    ''' Custom phase class for implementing some new, as-yet unconcieved actions. '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(options, dependencies)
        self.options |= {
            'name': 'generate',
            'gen_src_dir': '{build_anchor}/gen',
            'gen_src_origin': '',
            'gen_sources': {},
        }
        self.options |= (options or {})

    def get_generated_source(self):
        ''' Make the path and content of our generated source. '''
        return { Path(f"{self.opt_str('gen_src_dir')}/{src_file}"): src
                 for src_file, src in self.opt_dict('gen_sources').items() }

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output files.'''
        for src_path in self.get_generated_source().keys():
            self.record_file_operation(
                None,
                FileData(src_path.parent, 'dir', self),
                'create directory')
            self.record_file_operation(
                FileData(Path(self.opt_str('gen_src_origin')), 'generator', self),
                FileData(src_path, 'source', self),
                'generate')

    def do_step_generate_source(self, action: Action, depends_on: list[Step] | Step | None,
                                source_code: str, origin_path: Path, src_path: Path) -> Step:
        ''' Performs a directory creation operation as an action step. '''
        def act(cmd: str, origin_path: Path, src_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if not src_path.exists() or input_path_is_newer(origin_path, src_path):
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = f'echo "{source_code}" > {src_path}'
        step = Step('generate source', depends_on, [origin_path],
                    [src_path], partial(act, cmd=cmd, origin_path=origin_path, src_path=src_path),
                    cmd)
        action.set_step(step)
        return step

    def do_action_build(self, action: Action):
        ''' Generate the source files for the build. '''
        def get_source_code(desired_src_path):
            for src_path, src in self.get_generated_source().items():
                if src_path == desired_src_path:
                    return src.replace('"', '\\"')
            raise RuntimeError('Cannot find the source!')

        dirs = {}
        all_dirs = [fd.path for fd in self.files.get_output_files('dir')]
        for direc in list(dict.fromkeys(all_dirs)):
            dirs[direc] = self.do_step_create_directory(action, None, direc)

        origin_path = Path(self.opt_str('gen_src_origin') or __file__)

        for file_op in self.files.get_operations('generate'):
            for out in file_op.output_files:
                source_code = get_source_code(out.path)
                self.do_step_generate_source(action, dirs[out.path.parent],
                                             source_code, origin_path, out.path)
