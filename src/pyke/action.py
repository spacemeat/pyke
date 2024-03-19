''' Things concerning phase actions. '''

from enum import Enum
from os.path import relpath
from pathlib import Path
import sys
from typing import Optional

from .utilities import ensure_list, ensure_tuple, set_color as c, WorkingSet, InvalidActionError

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
        return self.value >= 0

    def failed(self):
        return not self.succeeded()

class StepResult:
    '''
    Result of one step of an action.
    '''
    def __init__(self, step_name: str, step_input: str, step_output: str, shell_cmd: str,
                 code: ResultCode = ResultCode.NO_ACTION, info = None):
        self.step_name = step_name
        self.step_input = step_input
        self.step_output = step_output
        self.shell_cmd = shell_cmd
        self.code = code
        self.info = info

    def set_result(self, code = ResultCode.NO_ACTION, info = None):
        ''' Sets the step results to this object. '''
        self.code = code
        self.info = info

    def __bool__(self):
        return self.code.value >= 0

    def did_succeed(self):
        '''
        Quick ask if a step was successful.
        '''
        return bool(self)


class ActionResult:
    '''
    Result of an action.
    '''
    def __init__(self, action: str, step_results: StepResult | tuple[StepResult]):
        self.action = action
        self.results = ensure_tuple(step_results)

    def __bool__(self):
        return all((bool(step) for step in self.results))

class Step:
    def __init__(self, step_name: str, step_input: list | None = None,
                 step_output: list | None = None, command: str = ''):
        self.name = step_name
        self.inputs = step_input or []
        self.outputs = step_output or []
        self.command = command

class Result:
    def __init__(self, code: ResultCode, notes: str | None = None):
        self.code = code
        self.notes = notes

def color_path(path: Path | str):
    '''
    Returns a colorized and possibly CWD-relative version of a path.
    '''
    if isinstance(path, Path):
        path = str(path)
    if WorkingSet.report_relative_paths:
        path = relpath(path)
    path = Path(path)
    return f'{c("path_dk")}{path.parent}/{c("path_lt")}{path.name}{c("off")}'

def format_path_list(paths):
    '''
    Returns a colorized path or formatted list notation for a list of paths.
    '''
    paths = ensure_list(paths)
    if len(paths) == 0:
        return ''
    if len(paths) == 1:
        return color_path(paths[0])
    return f'{c("path_dk")}[{c("path_lt")}...{c("path_dk")}]{c("off")}'

def report_phase(action: str, phase: str, phase_type: str):
    '''
    Prints a phase summary.
    '''
    print (f'{c("phase_dk")}action: {c("phase_lt")}{action}{c("phase_dk")} - phase: '
           f'{c("phase_lt")}{phase}{c("phase_dk")} '
           f'({c("phase_lt")}{phase_type}{c("phase_dk")}):{c("off")}', end = '')

def report_error(action: str, phase: str, phase_type: str, err: str):
    '''
    Print an error string to the console in nice, bright red.
    '''
    report_phase(action, phase, phase_type)
    print (f'\n{err}')

def report_action_start(action: str, phase: str, phase_type: str):
    ''' Reports on the start of an action. '''
    if WorkingSet.verbosity > 0:
        report_phase(action, phase, phase_type)
        print ('')

def report_action_end(action: str, phase: str, phase_type: str, result: ResultCode):
    ''' Reports on the start of an action. '''
    if WorkingSet.verbosity > 1 and result.succeeded():
        report_phase(action, phase, phase_type)
        print (f'{c("phase_dk")} ... {c("success")}succeeded{c("off")}')
    elif WorkingSet.verbosity > 0 and result.failed():
        report_phase(action, phase, phase_type)
        print (f'{c("phase_dk")} ... {c("fail")}failed{c("off")}')

def report_step_start(step: Step):
    ''' Reports on the start of an action step. '''
    if WorkingSet.verbosity > 0:
        inputs = format_path_list(list(step.inputs))
        outputs = format_path_list(list(step.outputs))
        if len(inputs) > 0 or len(outputs) > 0:
            print (f'{c("step_lt")}{step.name}{c("step_dkt")}: {inputs}'
                   f'{c("step_dk")} -> {c("step_lt")}{outputs}{c("off")}', end='')

def report_step_end(step: Step, result: Result):
    ''' Reports on the end of an action step. '''
    if result.code != ResultCode.ALREADY_UP_TO_DATE:
        if WorkingSet.verbosity > 1:
            if len(step.command) > 0:
                print (f'\n{c("shell_cmd")}{step.command}{c("off")}', end='')
    if result.code.value >= 0:
        if WorkingSet.verbosity > 0:
            print (f'{c("step_dk")} ({c("success")}{result.code.name}{c("step_dk")}){c("off")}')
    elif result.code.value < 0:
        if WorkingSet.verbosity > 0:
            print (f'{c("step_dk")} ({c("fail")}{result.code.name}{c("step_dk")}){c("off")}')
        print (f'{result.notes}', file=sys.stderr)


old = """
class ActionStep:
    ''' Manages the creation of a StepResult using the "with" syntax. '''
    def __init__(self, step_name: str, step_input: str, step_output: str,
                 cmd: Optional[str]):
        self.step_result = StepResult(step_name, step_input, step_output, cmd or '')
        report_step_start(self.step_result)

    def __enter__(self):
        return self.step_result

    def __exit__(self, *args):
        report_step_end(self.step_result)
        return False
"""

class StepAction:
    def __init__(self, step: Step):
        self.step = step
        self.result: Result = Result(ResultCode.NO_ACTION, None)
        report_step_start(self.step)

    def get_result(self):
        return self.result.code

    def set_result(self, result: Result):
        self.result = result
        report_step_end(self.step, self.result)

class PhaseAction:
    def __init__(self, phase_name: str):
        self.name = phase_name
        self.current_step: str = ''
        self.steps = {}

    def get_result(self):
        res = ResultCode.NOT_YET_RUN
        for _, pv in self.steps.items():
            if not (res := pv.get_result()).succeeded():
                return res
        return res

    def set_step(self, step: Step):
        self.current_step = step.name
        #if self.current_step not in self.steps:
        self.steps[self.current_step] = StepAction(step)
        #else:
        #    return ResultCode.ALREADY_RUN

    def set_step_result(self, result: Result):
        if self.current_step:
            self.steps[self.current_step].set_result(result)
        else:
            raise InvalidActionError('No step set.')

class ProjectAction:
    def __init__(self, project_name: str):
        self.name = project_name
        self.current_phase: str = ''
        self.phases = {}

    def get_result(self):
        res = ResultCode.NOT_YET_RUN
        for _, pv in self.phases.items():
            if not (res := pv.get_result()).succeeded():
                return res
        return res

    def set_phase(self, phase_name: str):
        self.current_phase = phase_name
        if self.current_phase not in self.phases:
            self.phases[self.current_phase] = PhaseAction(phase_name)
            return ResultCode.NOT_YET_RUN
        return self.phases[self.current_phase].get_result()

    def set_step(self, step: Step):
        if self.current_phase:
            return self.phases[self.current_phase].set_step(step)
        raise InvalidActionError('No phase set.')

    def set_step_result(self, result: Result):
        if self.current_phase:
            self.phases[self.current_phase].set_step_result(result)
        else:
            raise InvalidActionError('No project set.')

class Action:
    next_ordinal = 0

    def __init__(self, action_name: str):
        self.name = action_name
        self.ordinal = Action.next_ordinal
        Action.next_ordinal += 1
        self.current_project: str = ''
        self.projects = {}

    def get_result(self):
        res = ResultCode.NOT_YET_RUN
        for _, pv in self.projects.items():
            if not (res := pv.get_result()).succeeded():
                return res
        return res

    def set_project(self, project_name: str):
        self.current_project = project_name
        if self.current_project not in self.projects:
            self.projects[self.current_project] = ProjectAction(project_name)
            return ResultCode.NOT_YET_RUN
        return self.projects[self.current_project].get_result()

    def set_phase(self, phase_name: str):
        if self.current_project:
            return self.projects[self.current_project].set_phase(phase_name)
        raise InvalidActionError('No project set.')

    def set_step(self, step: Step):
        if self.current_project:
            return self.projects[self.current_project].set_step(step)
        raise InvalidActionError('No project set.')

    def set_step_result(self, result: Result):
        if self.current_project:
            self.projects[self.current_project].set_step_result(result)
        else:
            raise InvalidActionError('No project set.')
