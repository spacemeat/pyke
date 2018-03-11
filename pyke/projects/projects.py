import os
import json
import importlib
from .project import project
from timer import timer
from error import PykeError
from terminal import terminal as t

class project_finder:
    def __init__(self):
        self.all_projects_found = True
        self.exhausted = False
        self.current_dir = os.getcwd()
        self.past_dirs = set()
        self.projects_in_order = list()
        self.projects_by_path = {}
        self.projects_by_name = {}
    
    def __getitem__(self, name):
        return self.projects_by_name[name]

    def load_all(self):
        self.load_until("*")
        if len(self.projects_in_order) > 0:
            self.all_projects_found = True
    
    def load_until(self, target_proj_name):
        target_names = set()
        
        def check_depends(proj):
            for dname in proj.depends_on:
                if dname not in self.projects_by_name:
                    target_names.add(dname)
                else:
                    # Just reference the first one.
                    proj_dep = self.projects_by_name[dname][0]
                    check_depends(proj_dep)
        if target_proj_name in self.projects_by_name:
            for proj in self.projects_by_name[target_proj_name]:
                check_depends(proj)
        else:
            target_names.add(target_proj_name)
            
#        print ("targets: {0}".format(" ".join(target_names)))
        
        self.all_projects_found = False
        if len(target_names) == 0:
            self.all_projects_found = True

        json_path = self.current_dir
        
        def upward_recurse(path):
            def downward_recurse(path):
                if self.all_projects_found or self.exhausted:
                    return
                
#                print ("Searching {0}".format(path))

                # if we ended a search here, we don't want to re-process this pyke.json
                skip_this_file = False
                if path in self.past_dirs:
                    skip_this_file = True
                else:
                    self.past_dirs.add(path)

                file_path = os.path.join(path, "pyke.json")
                json_data = None

                # look for pyke.json, unless we ended a previous search here
                if os.path.exists(file_path):
                    with open(file_path) as f:
                        json_data = json.loads(f.read())
#                        print ("Found JSON:\n{0}".format(json_data))
                        
                        # we would skip earlier, but we want the json data to get depends-on
                        if "projects" in json_data and skip_this_file == False:
                            for proj_json in json_data["projects"]:
                                print ("Loading project - {0}".format(t.make_project_name(proj_json["name"])))
                                np = self.make_new_project(path, proj_json)
                                timer.mark("Load project '{}'".format(np.name))
                                key = "{0}/{1}".format(path, np.name)
                                
                                self.projects_in_order.append((key, np))
                                self.projects_by_path[key] = np
                                if np.name not in self.projects_by_name:
                                    self.projects_by_name[np.name] = list()
                                self.projects_by_name[np.name].append(np)
                                
                                if np.name in target_names:
#                                    print ("Found target: {0}".format(np.name))
                                    target_names.remove(np.name)

                                    if "depends-on" in proj_json:
                                        for dep in proj_json["depends-on"]:
                                            if dep not in self.projects_by_name:
#                                                print ("New target from {1}: {0}".format(dep, np.name))
                                                target_names.add(dep)

                                if len(target_names) == 0:
                                    self.all_projects_found = True
                
                # look down the hierarchy if we have dependencies
                if self.all_projects_found == False:
                    if json_data != None and "depends-on" in json_data:
                        for subdir in json_data["depends-on"]:
                            down_path = os.path.join(path, subdir)
                            if down_path not in self.past_dirs:
                                downward_recurse(os.path.join(path, subdir))
                                if self.all_projects_found:
                                    break
                
            downward_recurse(path)

            if self.all_projects_found == False and not self.exhausted:
                (_, basepath) = os.path.splitdrive(path)
                if basepath != "/":
                    path = os.path.normpath(os.path.join(path, ".."))
                    upward_recurse(path)
                else:
                    self.exhausted = True

        upward_recurse(json_path)

        if target_proj_name in self.projects_by_name:
            def load_deps(parent_proj):
                for name, proj in parent_proj.depends_on.items():
                    if proj == None:
                        self.load_until(name)
                        proj = self.projects_by_name[name][0]
                        #print (proj)
                        parent_proj.depends_on[name] = proj
                        load_deps(proj)
            load_deps(self.projects_by_name[target_proj_name][0])
        else:
            raise PykeError("Project {} not found.".format(t.make_project_name(target_proj_name)))

    def make_new_project(self, path, proj_json):
        m = importlib.import_module(''.join(['.', proj_json["type"]]), 'projects')
        np = m.make_project(path, proj_json)
        #np = project.project(path, proj_json) # new project instance
        return np

projects = project_finder()

