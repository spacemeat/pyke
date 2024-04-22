''' Phase for running a general command.'''

from functools import partial
from pathlib import Path
from ..action import Action, Step, Result, ResultCode
from .phase import Phase
from ..utilities import do_shell_command, any_input_paths_are_newer

class CommandPhase(Phase):
    ''' Phase to run an arbitrary shell command. It likely makes sense to subclass this phase for
    each command which manipulates files, so you can implement compute_file_operations(). '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(options, dependencies)
        self.options |= {
            'name': 'command',
            'posix_command': '',
            ##'windows_command': '',
            'commands': '{{target_os}_command}'
        }
        self.options |= (options or {})

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output files.'''

    def do_step_run_command(self, action: Action, depends_on: list[Step] | Step | None,
                            input_paths: list[Path], output_paths: list[Path]) -> Step:
        ''' Performs a shell command as an action step. '''
        def act(cmd: str, input_paths: list[Path], output_paths: list[Path]):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            missing_objs = []

            for obj_path in input_paths:
                if not obj_path.exists():
                    missing_objs.append(obj_path)
            if len(missing_objs) > 0:
                step_result = ResultCode.MISSING_INPUT
                step_notes = missing_objs
            else:
                if any_input_paths_are_newer(input_paths, output_paths):
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, str(step_notes))

        cmd = self.opt_str('command')
        step = Step('run command', depends_on, input_paths,
                    [], partial(act, cmd, input_paths, output_paths),
                    cmd)
        action.set_step(step)
        return step

    def do_action_build(self, action: Action):
        ''' Run the shell command as a build action. '''
        input_paths = []
        output_paths = []
        for file_op in self.files.get_operations('generate'):
            for inp in file_op.input_files:
                input_paths.append(inp.path)
            for out in file_op.output_files:
                output_paths.append(out.path)

        self.do_step_run_command(action, None, input_paths, output_paths)
