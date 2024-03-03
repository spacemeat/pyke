from enum import Enum
import sys
from typing import Optional

from . import ansi as a
from .utilities import ensure_tuple, set_color as c, WorkingSet

class ResultCode(Enum):
    '''
    Encoded result of one step of an action. Values >= 0 are success codes.
    '''
    NO_ACTION = 0
    SUCCEEDED = 1
    ALREADY_UP_TO_DATE = 2
    MISSING_INPUT = -1
    COMMAND_FAILED = -2
    DEPENDENCY_ERROR = -3
    INVALID_OPTION = -4


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

def report_phase(phase: str, action: str):
    '''
    Prints a phase summary.
    '''
    print (f'{c("phase_lt")}{action}{c("phase_dk")} - phase: {c("phase_lt")}'
           f'{phase}{c("phase_dk")}:{a.off}')

def report_error(phase: str, action: str, err: str):
    '''
    Print an error string to the console in nice, bright red.
    '''
    report_phase(phase, action)
    print (f'{err}')

def report_action_start(phase: str, action: str):
    ''' Reports on the start of an action. '''
    if WorkingSet.verbosity > 0:
        report_phase(phase, action)

def report_action_end(success: bool):
    ''' Reports on the start of an action. '''
    if WorkingSet.verbosity > 1 and success:
        print (f'{c("phase_dk")} ... {c("success")}succeeded{a.off}')
    elif WorkingSet.verbosity > 0 and not success:
        print (f'{c("phase_dk")} ... {c("fail")}failed{a.off}')

def report_step_start(result: StepResult):
    ''' Reports on the start of an action step. '''
    if WorkingSet.verbosity > 0:
        print (f'{c("step_dk")}{result.step_name} {c("step_lt")}{result.step_input}'
               f'{c("step_dk")} -> {c("step_lt")}{result.step_output}{a.off}', end='')
    if WorkingSet.verbosity > 1:
        print (f'\n{c("shell_cmd")}{result.shell_cmd}{a.off}', end='')

def report_step_end(result: StepResult):
    ''' Reports on the end of an action step. '''
    if result.code.value >= 0:
        if WorkingSet.verbosity > 0:
            print (f'{c("step_dk")} ({c("success")}{result.code.name}{c("step_dk")}){a.off}')
    elif result.code.value < 0:
        if WorkingSet.verbosity > 0:
            print (f'{c("step_dk")} ({c("fail")}{result.code.name}{c("step_dk")}){a.off}')
        print (f'{result.info}', file=sys.stderr)


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
