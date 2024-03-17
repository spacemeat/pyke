'''
This is the base Phase class for all other Phase types. All the base functionality
is contained herein.
'''

from pathlib import Path
from typing import Type, TypeVar, Iterable
from typing_extensions import Self

from ..action import (StepResult, ActionResult, ResultCode,
                      report_action_start, report_action_end, report_error)
from ..options import Options, OptionOp
from ..utilities import (ensure_list, WorkingSet, set_color as c,
                         InvalidOptionKey, CircularDependencyError)

T = TypeVar('T')

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
            'name': 'phase',
            'report_verbosity': 2,
            'verbosity': 0,
            'project_anchor': WorkingSet.makefile_dir,
            'gen_anchor': WorkingSet.makefile_dir,
            'simulate': False,
            'colors_24bit': {
                'off':              {'form': 'named', 'off': [] },
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
                'token_type':       {'form': 'rgb24', 'fg': [0x33, 0xff, 0xff] },
                'token_value':      {'form': 'rgb24', 'fg': [0xff, 0x33, 0xff] },
                'token_depth':      {'form': 'rgb24', 'fg': [0x33, 0xff, 0x33] },
            },
            'colors_named': {
            },
            'colors_none': {
                'off':              {},
                'success':          {},
                'fail':             {},
                'phase_lt':         {},
                'phase_dk':         {},
                'step_lt':          {},
                'step_dk':          {},
                'shell_cmd':        {},
                'key':              {},
                'val_uninterp_dk':  {},
                'val_uninterp_lt':  {},
                'val_interp':       {},
                'token_type':       {},
                'token_value':      {},
                'token_depth':      {},
            },
            'colors': '{colors_24bit}',
        }
        self.options |= options

        assert isinstance(options, dict)
        self.default_action = 'report'
        self.last_action_ordinal = -1
        self.last_action_result = None

        self.override_project_dependency_options = False

        if dependencies is None:
            dependencies = []
        dependencies = ensure_list(dependencies)
        self.dependencies = []
        for dep in dependencies:
            self.set_dependency(dep)

    def push_opts(self, overrides: dict):
        '''
        Apply optinos which take precedence over self.overrides. Intended to be 
        set temporarily, likely from the command line.
        '''
        self.options |= overrides
        for dep in self.dependencies:
            if dep.opt_str('build_operation') != 'project' or self.override_project_dependency_options:
                dep.push_opts(overrides)

    def pop_opts(self, keys: list[str]):
        '''
        Removes pushed option overrides.
        '''
        for dep in reversed(self.dependencies):
            if dep.opt_str('build_operation') != 'project' or self.override_project_dependency_options:
                dep.pop_opts(keys)
        for key in keys:
            self.options.pop(key)

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

    def opt_t(self, obj_type: Type[T], key: str, overrides: dict | None = None,
              interpolate: bool = True) -> T:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a tuple.
        '''
        val = self.opt(key, overrides, interpolate)
        assert isinstance(val, obj_type)
        return val

    def opt_iter(self, key: str, overrides: dict | None = None,
                 interpolate: bool = True) -> Iterable:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a tuple.
        '''
        return self.opt_t(Iterable, key, overrides, interpolate)

    def opt_bool(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> bool:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a bool.
        '''
        return self.opt_t(bool, key, overrides, interpolate)

    def opt_int(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> int:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be an int.
        '''
        return self.opt_t(int, key, overrides, interpolate)

    def opt_float(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> float:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a float.
        '''
        return self.opt_t(float, key, overrides, interpolate)

    def opt_str(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> str:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a string.
        '''
        return self.opt_t(str, key, overrides, interpolate)

    def opt_tuple(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> tuple:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a tuple.
        '''
        return self.opt_t(tuple, key, overrides, interpolate)

    def opt_list(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> list:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a list.
        '''
        val = self.opt(key, overrides, interpolate)
        assert isinstance(val, list)
        return val

    def opt_set(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> set:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a set.
        '''
        val = self.opt(key, overrides, interpolate)
        assert isinstance(val, set)
        return val

    def opt_dict(self, key: str, overrides: dict | None = None, interpolate: bool = True) -> dict:
        '''
        Returns an option's value, given its key. The option is optionally
        interpolated (by default) with self.options as its local namespace.
        The referenced value must be a dict.
        '''
        val = self.opt(key, overrides, interpolate)
        assert isinstance(val, dict)
        return val

    def __str__(self):
        return str(self.opt_str("name"))

    def __repr__(self):
        return str(self.opt_str("name"))

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

    def find_in_dependency_tree(self, dep_to_find: Self):
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
            if new_dep.find_in_dependency_tree(self) is not None:
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

        # set this on every do(), so each phase still controls its own verbosity, colors, etc
        WorkingSet.report_verbosity = self.opt_int('report_verbosity')
        WorkingSet.verbosity = self.opt_int('verbosity')
        if cols := self.opt('colors'):
            if isinstance(cols, dict):
                WorkingSet.colors = cols

        # TODO: New action stuff.
        #action.set_phase(self.opt_str('name'))

        action_ordinal = self._get_action_ordinal(action_ordinal)
        if self.last_action_ordinal == action_ordinal:
            self.last_action_result = ActionResult(
                action,
                StepResult('', '', '', '', ResultCode.ALREADY_UP_TO_DATE,
                f'{self.opt_str("name")}.{action}'))
            return self.last_action_result
        self.last_action_ordinal = action_ordinal

        for dep in self.dependencies:
            if dep.opt_str('build_operation') == 'project':
                res = dep.do(action, action_ordinal)
                if not res:
                    self.last_action_result = ActionResult(
                        action,
                        StepResult('', '', '', '', ResultCode.DEPENDENCY_ERROR, dep))
                    return self.last_action_result

        for dep in self.dependencies:
            if dep.opt_str('build_operation') != 'project':
                res = dep.do(action, action_ordinal)
                if not res:
                    self.last_action_result = ActionResult(
                        action,
                        StepResult('', '', '', '', ResultCode.DEPENDENCY_ERROR, dep))
                    return self.last_action_result

        action_method = getattr(self, 'do_action_' + action, self.do_action_undefined)
        try:
            report_action_start(str(self.opt_str('name')), action)
            self.last_action_result = action_method()

        except InvalidOptionKey as e:
            self.last_action_result = ActionResult(
                action,
                StepResult('', '', '', '', ResultCode.INVALID_OPTION, e))
            report_error(str(self.opt_str('name')), action, str(e))

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
        if WorkingSet.report_verbosity >= 0:
            report = f'phase: {self.opt_str("name")}'
            #pass
        if WorkingSet.report_verbosity >= 1:
            opts_str = ''
            for k in self.options.keys():
                vu = self.options.get(k, False)
                vi = self.options.get(k)

                assert isinstance(vu, list)

                indent = 0
                opts_str = ''.join((opts_str,
                                    f'{c("key")}{k}: '))
                last_replace_idx = len(vu) - next(i for i, e in enumerate(reversed(vu))
                    if e[1] == OptionOp.REPLACE) - 1
                if WorkingSet.report_verbosity >= 2:
                    for i, vue in enumerate(vu):
                        color = (c("val_uninterp_dk") if i < last_replace_idx
                                 else c("val_uninterp_lt"))
                        op = vue[1].value if isinstance(vue[1], OptionOp) else ' '
                        indent = 0 if i == 0 else len(k) + 2
                        opts_str = ''.join((opts_str,
                                            f'{" " * indent}{color}{op} {vue[0]}{c("off")}\n'))
                    indent = len(k) + 1
                else:
                    indent = 0

                opts_str = ''.join((opts_str,
                                    f'{" " * indent}{c("val_interp")}-> {vi}\n'))

            report += f'\n{opts_str}{c("off")}'
        print (report)
        return ActionResult(
            'report', StepResult('report', '', '', '', ResultCode.NO_ACTION, str(self)))
