''' Things concerning phase actions. '''

from enum import Enum
from pathlib import Path
from typing_extensions import Self

from .utilities import ensure_list, InvalidActionError

# pylint: disable=too-few-public-methods

class ResultCode(Enum):
    '''
    Encoded result of one step of an action. Values >= 0 are success codes.
    '''
    NO_ACTION = 0
    SUCCEEDED = 1
    ALREADY_UP_TO_DATE = 2
    ALREADY_RUN = 3
    NOT_YET_RUN = 4
    MISSING_INPUT = -1
    COMMAND_FAILED = -2
    DEPENDENCY_ERROR = -3
    INVALID_OPTION = -4

    def succeeded(self):
        ''' Returns whether a particular value is considered a success.'''
        return self.value >= 0

    def failed(self):
        ''' Returns whether a particular value is considered a failure (strictly not a success).'''
        return not self.succeeded()


class FileData:
    def __init__(self, path: Path, file_type: str, generating_phase: 'Phase'):
        self.path = path
        self.file_type = file_type
        self.generating_phase = generating_phase

class FileOperation:
    def __init__(self, input_files: list[FileData] | FileData | None,
                 output_files: list[FileData] | FileData | None, step_name: str):
        self.input_files = ensure_list(input_files) if input_files is not None else []
        self.output_files = ensure_list(output_files) if output_files is not None else []
        self.step_name = step_name

class PhaseFiles:
    def __init__(self):
        self.operations = []

    def record(self, operation: FileOperation):
        ''' Records a file transform operation.'''
        self.operations.append(operation)

    def get_operations(self, step_name):
        ''' Returns all recorded inputs and outputs for a gven operation type.'''
        return [op for op in self.operations if op.step_name == step_name]

    def get_input_files(self, file_type):
        ''' Returns all recorded outputs of a given type.'''
        return [file_data for op in self.operations
                          for file_data in op.input_files if file_data.file_type == file_type]

    def get_output_files(self, file_type):
        ''' Returns all recorded outputs of a given type.'''
        return [file_data for op in self.operations
                          for file_data in op.output_files if file_data.file_type == file_type]

class StepFunction:
    def __init__(self, fn: callable):
        self.fn = fn

class StepCommand(StepFunction):
    def __init__(self, command: str):
        self.command = command

#Steps: TypeAlias = list['Step'] | 'Step' | None


class Step:
    ''' Represents a single step in a phase's action. These are dynamically added as needed.'''
    def __init__(self, name: str, depends_on: list[Self] | Self | None, inputs: list[FileData],
                 outputs: list[FileData], act_fn: callable, command: str = ''):
        self.name = name
        self.depends_on = ensure_list(depends_on) if depends_on is not None else []
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.act_fn = act_fn
        self.command = command
        self.result = None

    def run(self):
        ''' Runs the act function if its depend_on steps all succeeded.'''
        final_res = ResultCode.SUCCEEDED
        for step in self.depends_on:
            res = step.result.code
            if res.failed() and final_res.succeeded():
                final_res = res
        if final_res.failed():
            return final_res
        self.result = self.act_fn()
        return self.result.code

class Result:
    ''' Represents the results of a Step.'''
    def __init__(self, code: ResultCode, notes: str | None = None):
        self.code = code
        self.notes = notes

class PhaseAction:
    ''' Records an action's phases within a project phase.'''
    def __init__(self, phase: str):
        self.name = phase.name
        self.phase = phase
        self.current_step: str = ''
        self.steps = []

    def __repr__(self):
        s = f'    {self.phase.name} - current_step = {self.current_step}'
        s += ''.join([repr(st) for st in self.steps])
        return s

    def get_result(self):
        ''' Gets the result code.'''
        res = ResultCode.NOT_YET_RUN
        for pv in self.steps:
            res = pv.get_result()
            if not res.succeeded():
                break
        return res if res.failed() else ResultCode.SUCCEEDED

    def set_step(self, step: Step):
        ''' Begins recording a step.'''
        self.steps.append(step)

    def run(self, action_name: str):
        ''' Run all the steps recorded for this phase.'''
        must_report_phase = len(self.steps) > 0
        if must_report_phase:
            self.phase.report_action_phase_start(
                action_name, self.name, type(self.phase).__name__)
        final_res = ResultCode.SUCCEEDED
        for step in self.steps:
            self.phase.report_step_start(step)
            res = step.run()
            self.phase.report_step_end(step)
            if res.failed() and final_res.succeeded():
                final_res = res
        if must_report_phase:
            self.phase.report_action_phase_end(
                action_name, self.name, type(self.phase).__name__, final_res)
        return final_res

class ProjectAction:
    ''' Records an action's project phases.'''
    def __init__(self, project_name: str):
        self.name = project_name
        self.current_phase: str = ''
        self.phases = {}

    def __repr__(self):
        s = f'  {self.name} - current_phase = {self.current_phase}'
        s += ''.join([repr(ph) for ph in self.phases])
        return s

    def get_result(self):
        ''' Gets the result code.'''
        res = ResultCode.NOT_YET_RUN
        for pv in self.phases:
            res = pv.get_result()
            if not res.succeeded():
                break
        return res if res.failed() else ResultCode.SUCCEEDED

    def set_phase(self, phase: 'Phase'):
        ''' Begins recording a non-project phase.'''
        self.current_phase = phase.name
        if self.current_phase not in self.phases:
            self.phases[self.current_phase] = PhaseAction(phase)
            return ResultCode.NOT_YET_RUN
        return ResultCode.ALREADY_RUN

    def set_step(self, step: Step):
        ''' Begins recording a step.'''
        if self.current_phase:
            return self.phases[self.current_phase].set_step(step)
        raise InvalidActionError('No phase set.')

    def run(self, action_name: str):
        ''' Run all the steps recorded for this project.'''
        final_res = ResultCode.SUCCEEDED
        for _, phase in self.phases.items():
            res = phase.run(action_name)
            if res.failed() and final_res.succeeded():
                final_res = res
        return final_res

class Action:
    ''' Records an action's flow through phases and results.'''
    def __init__(self, action_name: str):
        self.name = action_name
        self.current_project: str = ''
        self.projects = {}

    def __repr__(self):
        s = f'{self.name} - current_phase = {self.current_project}'
        s += ''.join([repr(pr) for pr in self.projects])
        return s

    def get_result(self):
        ''' Gets the result code.'''
        res = ResultCode.NOT_YET_RUN
        for pv in self.projects:
            res = pv.get_result()
            if not res.succeeded():
                break
        return res if res.failed() else ResultCode.SUCCEEDED

    def set_project(self, project_name: str):
        ''' Begins recording a project phase.'''
        self.current_project = project_name
        if self.current_project not in self.projects:
            self.projects[self.current_project] = ProjectAction(project_name)
            return ResultCode.NOT_YET_RUN
        return ResultCode.ALREADY_RUN

    def set_phase(self, phase_name: str):
        ''' Begins recording a non-project phase.'''
        if self.current_project:
            return self.projects[self.current_project].set_phase(phase_name)
        raise InvalidActionError('No project set.')

    def set_step(self, step: Step):
        ''' Begins recording a step.'''
        if self.current_project:
            return self.projects[self.current_project].set_step(step)
        raise InvalidActionError('No project set.')

    def run(self):
        ''' Run all the steps recorded for this action.'''
        final_res = ResultCode.SUCCEEDED
        for _, project in self.projects.items():
            res = project.run(self.name)
            if res.failed() and final_res.succeeded():
                final_res = res
        return final_res
