''' Custom phase for pyke project.'''

from pathlib import Path
from pyke import (CFamilyBuildPhase, Action, ResultCode, Step, Result,
                  input_path_is_newer, do_shell_command)

gen_src = {
        'd.c': r'''
#include \"abc.h\"

int d()
{
	return 1000;
}''',
        'e.c': r'''
#include \"abc.h\"

int e()
{
	return 10000;
}'''
}

class ContrivedCodeGenPhase(CFamilyBuildPhase):
    '''
    Custom phase class for implementing some new, as-yet unconcieved actions.
    '''
    def __init__(self, name: str | None = None, options: dict | None = None, dependencies = None):
        options = {
            'gen_src_dir': '{build_anchor}/gen',
        } | (options or {})
        super().__init__(name, options, dependencies)

    def make_generated_source(self):
        '''
        Make the path and content of our generated source.
        '''
        return { Path(f"{self.opt_str('gen_src_dir')}/{src_file}"): src
                 for src_file, src in gen_src.items() }

    def do_action_clean(self, action: Action):
        '''
        Cleans all object paths this phase builds.
        '''
        res = ResultCode.SUCCEEDED
        for src_path, _ in self.make_generated_source().items():
            res = res.failed() or self.do_step_delete_file(src_path, action)
        return res

    def do_action_clean_build_directory(self, action: Action):
        '''
        Wipes out the generated source directory.
        '''
        return self.do_step_delete_directory(Path(self.opt_str('gen_src_dir')), action)

    def do_action_build(self, action: Action):
        '''
        Generate the source files for the build.
        '''
        self_path = Path(__file__)

        for src_path, src in self.make_generated_source().items():
            if self.do_step_create_directory(src_path.parent, action).succeeded():

                cmd = f'echo "{src}" > {src_path}'
                step_result = ResultCode.SUCCEEDED
                step_notes = None
                action.set_step(Step('generate', [self_path], [src_path], cmd))

                if not src_path.exists() or input_path_is_newer(self_path, src_path):
                    res, _, err = do_shell_command(cmd)
                    if res != 0:
                        step_result = ResultCode.COMMAND_FAILED
                        step_notes = err
                    else:
                        step_result = ResultCode.SUCCEEDED
                else:
                    step_result = ResultCode.ALREADY_UP_TO_DATE

                action.set_step_result(Result(step_result, step_notes))

        return action.get_result()
