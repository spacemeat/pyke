def run_list_projects(command, projs):
    for project in command.children:
        name = project.name
        projs.load_until(name)
        print ("{0} at {1}".format(name, projects(project.name)))
    

