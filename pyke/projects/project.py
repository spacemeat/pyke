import os
import json
from JsonData import JsonData
from terminal import terminal as t
from timer import timer
import inspect

#print (dir(projects))

#for o in dir(projects):
#    print ("{}:".format(o))
#    for k in dir(o):
#        print ("  {}: {}".format(k, getattr(o, k)))

    
#"pyke fracto: config: debug; set: version, 2.1.0; build"


class project():
    def __init__(self, path, json_data = {}):
        self.path = path
        self.name = get_json_val(json_data, "name", "<nu>")
        self.applied_configs = []
        self.project_type = get_json_val(json_data, "type", "project")
        self.depends_on = dict()

        if "depends-on" in json_data:
            for dp in json_data["depends-on"]:
                self.depends_on[dp] = None

        self.json_data = dict()
        self._apply_template()
        self._apply_json_additive(json_data)
        
        self.json_commands = dict()
        self.map_json_commands()


    def map_json_commands(self):
        if 'commands' in self.json_data:
            for com in self.json_data['commands']:
                if 'name' in com:
                    self.json_commands[com['name']] = com
                

    def run_command(self, command):
        recipe = self._get_recipe(command)
        if len(recipe) == 0:
            raise PykeError("{0}: Invalid command \"{1}\"".format(
                t.make_project_name(self.name),
                t.make_command(command.name)))
        for step in recipe:
            step_name = "{0}.{1}.{2}".format(
                t.make_project_name(self.name),
                t.make_command(command.name),
                t.make_step(step))
            step_name_nc = "{0}.{1}.{2}".format(self.name, command.name, step)
            print ("Running {0}:".format(t.make_step(step_name)))
            try:
                self._run_op(command, step)
            finally:
                timer.mark("Run '{}'".format(step_name_nc))
        

    def _get_recipe(self, command):
        if (command.name in self.json_commands):
            return self.json_commands[command.name]['recipe']
        else:
            return []

    
    def _get_command_docs(self, command):
        if (command.name in self.json_commands):
            return self.json_commands[command.name]['doc']
        else:
            return {}


    def _run_op(self, command, step):
        m = getattr(self, "_run_op_{0}".format(step), None)
        if m != None:
            return m(command)
        else:
            raise PykeError("No op named '{0}' could be found.".format(t.make_step(step)))
            
    
    def _run_op_describe(self, command):
        verbose = False
        for switch in command.children:
            if switch.name == "verbose":
                verbose = True
            if switch.name == "terse":
                verbose = False

        print ("")
        if verbose:
            print ('=' * 60)
        print ("Project {0}\nat {1}\nType: {2}\nVersion: {3}\n".format(
            t.make_project_name(self.name),
            t.make_project_path(self.path),
            t.make_project_type(self.project_type),
            self.json_data['version']))
        
        print (self.json_data['doc']['short'])

        print ("\nAvailable commands:")

        if 'commands' in self.json_data:
            for cmd in self.json_data['commands']:
                cmd_name = cmd['name']
                print ("\t{0}: {1}".format(
                    t.make_command(cmd_name),
                    cmd['doc']['short']))
                for arg in cmd['doc']['args']:
                    arg_name = arg['name']
                    print ("\t\t{0}: {1}".format(
                        t.make_command_arg(arg_name), 
                        arg['short']))
                    if verbose and 'long' in arg:
                        print ("\t\t{0}".format(
                        t.make_command_arg_doc(arg['long'])))

                if verbose and 'long' in cmd['doc']:
                    print ("\t{0}\n".format(
                    t.make_command_doc(cmd['doc']['long'])))
        
        if verbose and 'long' in self.json_data['doc']:
            print (self.json_data['doc']['long'])
            
        if verbose:
            print ('=' * 60)
        print ("")
        
    
    def _run_op_config(self, command):
        if 'configurations' not in self.json_data:
            raise ValueError("No configurations defined in {0}.".format(t.make_project_name(self.name)))
        
        for config_cmds in command.children:
            name = config_cmds.name
            self._apply_config(name)
        

    def _apply_config(self, name):
        print ("Available configurations: {}".format(self.json_data['configurations'].keys()))
        if name not in self.json_data['configurations']:
            raise ValueError("No configuration named {0} defined in {1}.".format(
                t.make_configuration(name),
                t.make_project_name(self.name)))
        print ("Applying configuration {}.".format(
            t.make_configuration(name)))
        self._apply_json_additive(self.json_data['configurations'][name])
        self.applied_configs.append(name)
            
    
    def _run_op_set(self, command):
        if len(command.children) != 2:
            raise ValueError("{0} command must have two arguments. {1} given.".format(command.name, len(command.children)))
        
        self.json_data[command.children[0].name] = command.children[1].name
        
        
    def _run_op_add(self, command):
        if len(command.children) < 2:
            raise ValueError("{0} command must have at least two argument".format(t.make_command(command.name)))
        cname = command.children[0].name
        if cname not in self.json_data:
            self.json_data[cname] = []
        for ch in command.children[1:]:
            self.json_data[cname].append(ch.name)
            
    
    def _apply_template(self):
    #    if template in self.path
    #    elif template in ~/.pyke_templates
    #    elif template in pyke/projects
        # get each class name up the hierarchy to project, and work back to 
        # load each template        
        bases = []
        ptype = self.__class__
        while True:
            bases.append(ptype.__name__)
            if (ptype.__name__ == 'project' or
                len(ptype.__bases__) == 0):
                break
            ptype = ptype.__bases__[0]
        bases.reverse()
        
        # For each base, find its template separately in each location type.
        # Interesting: You can override a template of any base, including 
        # project_template.json.
        for base in bases:
            template_name = ''.join([base, "_template.json"])
            path_template = os.path.join(self.path, template_name)
            home_template = os.path.abspath(os.path.join("~/.pyke_templates", template_name))
            lib_template = os.path.join(os.path.dirname(__file__), template_name)
            
            if os.path.exists(path_template):
                self._load_template_json(path_template)
            elif os.path.exists(home_template):
                self._load_template_json(home_template)
            elif os.path.exists(lib_template):
                self._load_template_json(lib_template)
            else:
                print ("No template loaded for base {0}.".format(base))


    def _load_template_json(self, full_path):
#        print ("Loading template {0}".format(full_path))
        with open(full_path) as f:
            json_data = json.loads(f.read())
            self._apply_json_additive(json_data)


    def _apply_default_configuration(self):
        if 'default-configuration' in self.json_data:
            self._apply_config(self.json_data['default-configuration'])

    
    def _apply_json_additive(self, json_data):
        _merge_json(self.json_data, json_data)
    

