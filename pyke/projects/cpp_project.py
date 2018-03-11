from terminal import terminal as t
from tools.cpp_tool import cpp_tool, cpp_data
from .project import project


class cpp_project(project):
    def __init__(self, path, json_data = {}):
        super().__init__(path, json_data)
        self.tool = cpp_tool(path)

    
    def _run_op_describe(self, command):
        super()._run_op_describe(command)
    

    def _run_op_config(self, command):
        for name, proj in self.depends_on.items():
            print ("Running {} on dependent project {}".format(
                t.make_command(command.name),
                t.make_project_name(name)))
            proj.run_command(command)
        super()._run_op_config(command)
            
    
    def _run_op_clean(self, command):
        data = cpp_data(self, self.json_data)
        self.tool.set_cpp_data(data)
        self.tool.clean_project()
        

    def _run_op_build(self, command):
        for name, proj in self.depends_on.items():
            print ("Running {} on dependent project {}".format(
                t.make_command(command.name),
                t.make_project_name(name)))
            proj.run_command(command)

        data = cpp_data(self, self.json_data)
        self.tool.set_cpp_data(data)
        self.tool.build_project()
        

    def _run_op_run(self, command):
        pass
        

    def _run_op_test(self, command):
        pass
        

def make_project(path, proj_json):
    return cpp_project(path, proj_json)


