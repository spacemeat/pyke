''' Reports verbose messages.'''

from os.path import relpath
from pathlib import Path
import sys

from .utilities import get_color_code, ensure_list

class Reporter:
    ''' Make one of these to print formatted reports.'''

    def __init__(self, option_owner):
        self.options = option_owner

    def c(self, color):
        ''' Returns a named color.'''
        return get_color_code(self.options.opt_dict('colors_dict'), color)

    def color_path(self, path: Path | str):
        ''' Returns a colorized and possibly CWD-relative version of a path. '''
        if isinstance(path, Path):
            path = str(path)
        if self.options.opt_bool('report_relative_paths'):
            path = relpath(path)
        path = Path(path)
        return f'{self.c("path_dk")}{path.parent}/{self.c("path_lt")}{path.name}{self.c("off")}'

    def format_path_list(self, paths):
        ''' Returns a colorized path or formatted list notation for a list of paths. '''
        paths = ensure_list(paths)
        if len(paths) == 0:
            return ''
        if len(paths) == 1:
            return self.color_path(paths[0])
        return f'{self.c("path_dk")}[{self.c("path_lt")}...{self.c("path_dk")}]{self.c("off")}'

    def color_phase(self, phase_type: str, phase_full_name: str): #phase: Phase):
        ''' Returns a colorized phase name and type.'''
        #phase_type = type(phase).__name__
        return (f'{self.c("phase_lt")}{phase_full_name}{self.c("phase_dk")} '
                f'({self.c("phase_lt")}{phase_type}{self.c("phase_dk")}){self.c("off")}')

    def color_file_type(self, file_type: str):
        ''' Returns a colorized file type.'''
        return f'{self.c("file_type_lt")}{file_type}{self.c("off")}'

    def format_file_data(self, phase_type: str, phase_full_name: str, file_path: str,
                         file_type: str):
        ''' Formats a FileData object for reporting.'''
        phase_name = self.color_phase(phase_type, phase_full_name)
        s = (f'    {self.color_path(file_path)}{self.c("step_dk")} - '
             f'{self.c("file_type_dk")}type: {self.color_file_type(file_type)}')
        if phase_full_name != '':
            s += (f'{self.c("step_dk")} - {self.c("phase_dk")}generated by: {phase_name}'
                  f'{self.c("off")}')
        else:
            s += f'{self.c("step_dk")} - {self.c("phase_dk")}(extant file){self.c("off")}'
        return s

    def color_file_step_name(self, step_name: str):
        ''' Colorize a FileOperation step name for reporting.'''
        return f'{self.c("step_lt")}{step_name}{self.c("off")}'

    def format_action(self, action_name: str):
        ''' Formats an action name for reporting.'''
        s = f'{self.c("action_dk")}action: {self.c("action_lt")}{action_name}{self.c("off")}'
        return s

    def format_phase(self, phase_type: str, phase_full_name: str):
        ''' Formats an action name for reporting.'''
        s = (f'{self.c("phase_dk")}phase: {self.color_phase(phase_type, phase_full_name)}'
             f'{self.c("phase_dk")}:{self.c("off")}')
        return s

    def report_phase(self, action: str, phase_type: str, phase_full_name: str):
        ''' Prints a phase summary. '''
        print (f'{self.format_action(action)}{self.c("action_dk")} - '
               f'{self.format_phase(phase_type, phase_full_name)}', end = '')

    def report_error(self, action: str, phase_type: str, phase_full_name: str, err: str):
        ''' Print an error string to the console in nice, bright red. '''
        self.report_phase(action, phase_type, phase_full_name)
        print (f'\n{err}')

    def report_action_phase_start(self, action: str, phase_type: str, phase_full_name: str):
        ''' Reports on the start of an action. '''
        if self.options.opt_int('verbosity') > 0:
            self.report_phase(action, phase_type, phase_full_name)
            print ('')

    def report_action_phase_end(self, result_succeeded: bool):
        ''' Reports on the start of an action. '''
        verbosity = self.options.opt_int('verbosity')
        if verbosity > 1 and result_succeeded:
            print (f'        {self.c("action_dk")}... action {self.c("success")}succeeded'
                   f'{self.c("off")}')
        elif verbosity > 0 and not result_succeeded:
            print (f'        {self.c("action_dk")}... action {self.c("fail")}failed{self.c("off")}')

    def report_step_start(self, step_name: str, input_paths: list[str], output_paths: list[str]):
        ''' Reports on the start of an action step. '''
        if self.options.opt_int('verbosity') > 0:
            inputs = self.format_path_list(input_paths)
            outputs = self.format_path_list(output_paths)
            if len(inputs) > 0 or len(outputs) > 0:
                print (f'{self.c("step_lt")}{step_name}{self.c("step_dk")}: {inputs}'
                       f'{self.c("step_dk")} -> {self.c("step_lt")}{outputs}{self.c("off")}',
                       end='')

    def report_step_end(self, command: str, result_succeeded: bool, result_message: str,
                        result_notes: str):
        ''' Reports on the end of an action step. '''
        verbosity = self.options.opt_int('verbosity')
        if result_message != 'already up to date':
            if verbosity > 1:
                if len(command) > 0:
                    print (f'\n{self.c("shell_cmd")}{command}{self.c("off")}', end='')
        if result_succeeded:
            if verbosity > 0:
                print (f'{self.c("step_dk")} - {self.c("success")}{result_message}'
                       f'{self.c("step_dk")}{self.c("off")}')
        elif not result_succeeded:
            if verbosity > 0:
                print (f'{self.c("step_dk")} - {self.c("fail")}{result_message}'
                       f'{self.c("step_dk")}{self.c("off")}')
            if result_notes:
                print (f'{result_notes}', file=sys.stderr)
