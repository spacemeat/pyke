'''
This is the base Phase class for all other Phase types. All the base functionality
is contained herein.
'''

from pathlib import Path
from typing_extensions import Self

from ..action import (StepResult, ActionResult, ResultCode,
                      report_action_start, report_action_end, report_error)
from .. import ansi as a
from ..options import Options, OptionOp
from ..utilities import (ensure_list, WorkingSet, set_color as c,
                         InvalidOptionKey, CircularDependencyError)

class Phase:
    '''
    Serves as the base class for a derived PykePhase. Each derived 
    phase represents a relationship between inputs and outputs of 
    a build process. Each phase can support multiple actions such 
    as cleaning, building, running, archiving, etc. Some phases
    only have one obvious action to support; others might be
    referenced as dependencies of other phases. (Think phases that
    build objects from source as dependencies of a phase that builds
    a binary from objects.)

    Pyke comes built-in with numerous useful phase classes, and users
    can define their own to support bespoke processes.
    '''
    def __init__(self, options: dict, dependencies: Self | list[Self] | None = None):
        self.options = Options()
        self.options |= {
            'name': 'unnamed',
            'verbosity': 0,
            'project_anchor': WorkingSet.makefile_dir,
            'gen_anchor': WorkingSet.makefile_dir,
            'simulate': False,
            'colors_24bit': {
                'success':          {'form': 'rgb24', 'fg': [0x33, 0xaf, 0x55] },
                'fail':             {'form': 'rgb24', 'fg': [0xff, 0x33, 0x33] },
                'phase_lt':         {'form': 'rgb24', 'fg': [0x33, 0x33, 0xff] },
                'phase_dk':         {'form': 'rgb24', 'fg': [0x23, 0x23, 0x7f] },
                'step_lt':          {'form': 'rgb24', 'fg': [0x33, 0xaf, 0xaf] },
                'step_dk':          {'form': 'rgb24', 'fg': [0x23, 0x5f, 0x5f] },
                'shell_cmd':        {'form': 'rgb24', 'fg': [0x31, 0x31, 0x32] },
                'key':              {'form': 'rgb24', 'fg': [0xff, 0x8f, 0x23] },
                'val_uninterp_dk':  {'form': 'rgb24', 'fg': [0x5f, 0x13, 0x5f] },
                'val_uninterp_lt':  {'form': 'rgb24', 'fg': [0xaf, 0x23, 0xaf] },
                'val_interp':       {'form': 'rgb24', 'fg': [0x33, 0x33, 0xff] },
            },
            'colors_named': {
            },
            'colors_none': {
            },
            'colors': '{colors_24bit}',
        }
        self.options |= options

        assert isinstance(options, dict)
        self.default_action = 'report'
        self.last_action_ordinal = -1
        self.last_action_result = None

        if dependencies is None:
            dependencies = []
        dependencies = ensure_list(dependencies)
        self.dependencies = []
        for dep in dependencies:
            self.set_dependency(dep)

    def push_option_overrides(self, overrides: dict):
        '''
        Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line.
        '''
        self.options |= overrides
        for dep in self.dependencies:
            dep.push_option_overrides(overrides)

    def pop_option_overrides(self, keys: list):
        '''
        Removes pushed option overrides.
        '''
        for dep in reversed(self.dependencies):
            dep.pop_option_overrides(keys)
        for key in keys:
            self.options.pop(key)

    def lopt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        '''
        if overrides:
            self.options |= overrides
        val = self.options.get(key, interpolate)
        if overrides:
            for k in overrides.keys():
                self.options.pop(k)
        return val

    def sopt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        '''
        if overrides:
            self.options |= overrides
        val = self.options.get(key, interpolate)
        if overrides:
            for k in overrides.keys():
                self.options.pop(k)
        return val

    def opt(self, key: str, overrides: dict | None = None, interpolate: bool = True):
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        '''
        if overrides:
            self.options |= overrides
        val = self.options.get(key, interpolate)
        if overrides:
            for k in overrides.keys():
                self.options.pop(k)
        return val

    def __str__(self):
        return str(self.sopt("name"))

    def __repr__(self):
        return str(self.sopt("name"))

    def clone(self, options: dict | None = None):
        '''
        Returns a clone of this instance. The clone has the same
        options (also copied) but its own dependencies and action
        results state.
        '''
        obj = type(self)({})
        obj.options = self.options.clone()
        obj.options |= options or {}
        return obj

    def is_in_dependency_tree(self, dep_to_find: Self):
        '''
        Returns whether dep_to_find is in the dependency tree for 
        this phase.
        '''
        try:
            idx = self.dependencies.index(dep_to_find)
            return self.dependencies[idx]
        except ValueError:
            for dep in self.dependencies:
                phase = dep.find_in_dependency_tree(dep_to_find)
                if phase is not None:
                    return phase
            return None

    def set_dependency(self, new_deps: Self | list[Self]):
        '''
        Marks a dependency phase for this phase. Must not be a phase
        which does not depend on this phase already (no circular 
        references allowed).
        '''
        new_deps = ensure_list(new_deps)
        for new_dep in new_deps:
            if new_dep.is_in_dependency_tree(self) is not None:
                raise CircularDependencyError(
                    f'Attempt to set a circular dependency {str(new_dep)} '
                    f'to phase {str(self)}. Not cool.')
            self.dependencies.append(new_dep)

    def _get_action_ordinal(self, action_ordinal: int):
        '''
        Replaces the default action_ordinal with the proper internal tracking
        ordinal.
        '''
        if action_ordinal == -1:
            return self.last_action_ordinal + 1
        return action_ordinal

    def make_cmd_delete_file(self, path: Path):
        '''
        Returns an appropriate command for deleting a file.
        '''
        return f'rm {str(path)}'

    def do(self, action: str, action_ordinal: int = -1) -> ActionResult:
        '''
        Performs an action, such as 'build' or 'run'. 

        First, each dependency phase is called with the same action, depth-first.
        Next, the corresponding 'do_action_<action>' method is called for this
        phase.

        Each invoked action is bound to an action_ordinal, an integer which 
        specifies a particular action which is tracked to prevent repeat actions
        for phases which are dependents of multiple other phases. This is managed
        internally.
        '''

        # set this on every do(), so each phase still controls its own verbosity
        WorkingSet.verbosity = int(str(self.sopt('verbosity')))

        if cols := self.opt('colors'):
            if isinstance(cols, dict):
                WorkingSet.colors = cols

        action_ordinal = self._get_action_ordinal(action_ordinal)
        if self.last_action_ordinal == action_ordinal:
            self.last_action_result = ActionResult(
                action,
                StepResult('', '', '', '', ResultCode.ALREADY_UP_TO_DATE,
                f'{self.sopt("name")}.{action}'))
            return self.last_action_result

        self.last_action_ordinal = action_ordinal
        for dep in self.dependencies:
            res = dep.do(action, action_ordinal)
            if not res:
                self.last_action_result = ActionResult(
                    action,
                    StepResult('', '', '', '', ResultCode.DEPENDENCY_ERROR, dep))
                return self.last_action_result

        action_method = getattr(self, 'do_action_' + action, self.do_action_undefined)
        try:
            report_action_start(str(self.sopt('name')), action)
            self.last_action_result = action_method()

        except InvalidOptionKey as e:
            self.last_action_result = ActionResult(
                action,
                StepResult('', '', '', '', ResultCode.INVALID_OPTION, e))
            report_error(str(self.sopt('name')), action, str(e))

        report_action_end(bool(self.last_action_result))

        return self.last_action_result

    def do_action_undefined(self):
        '''
        This is the default action for actions that a phase does not support.
        Goes nowhere, does nothing.
        '''
        return ActionResult('', StepResult('', '', '', '', ResultCode.NO_ACTION))

    def do_action_report(self):
        '''
        This gives a small description of the phase.
        '''
        report = ''
        if WorkingSet.verbosity == 0:
            report = f'phase: {self.sopt("name")}'
        if WorkingSet.verbosity <= 1:
            opts_str = ''
            for k in self.options.keys():
                vu = self.options.get(k, False)
                vi = self.options.get(k)

                assert(isinstance(vu, list))

                opts_str = ''.join((opts_str,
                                    f'{c("key")}{k}: '))
                last_replace_idx = len(vu) - next(i for i, e in enumerate(reversed(vu))
                    if e[1] == OptionOp.REPLACE) - 1
                for i, vue in enumerate(vu):
                    color = (c("val_uninterp_dk") if i < last_replace_idx 
                             else c("val_uninterp_lt"))
                    indent = 0 if i == 0 else len(k) + 2
                    op = vue[1].value if isinstance(vue[1], OptionOp) else ' '
                    opts_str = ''.join((opts_str,
                                        f'{" " * indent}{color}{op} {vue[0]}{a.off}\n'))

                opts_str = ''.join((opts_str,
                                    f'{" " * (len(k) + 1)}{c("val_interp")}-> {vi}\n'))

            report = f'{report}\n{opts_str}'
            print (report)
        return ActionResult(
            'report', StepResult('report', '', '', '', ResultCode.NO_ACTION, str(self)))
