from projects.projects import projects
import command as com
import built_in
from error import PykeError
from terminal import terminal as t
from timer import timer
import tools.cpp_tool


def print_usage():
    print ("Usage:\n\tpyke [command [:arg [,arg...]]] [; command [:arg [,arg]]] [;...]");
    print ("\tpyke [project [command [:arg [,arg...];] [,command [:arg [,arg];];]] [; command [:arg [,arg]]] [;...]");
    

def run_project(command):
#    print ("Finding project {0}:".format(command.name))
    projects.load_until(command.name)

    if command.name in projects.projects_by_name:
        proj = projects.projects_by_name[command.name][0]
#        print ("Using {0}".format(proj.name))

        if len(command.children) > 0:
            for cmd in command.children:
                try:
                    proj.run_command(cmd)
                except PykeError as ve:
                    print ("{0}: {1}".format(t.make_error('Error'), ve))
                    break
        else:
            c = com.command("describe", command)
            command.children.append(c)
            proj.run_command(c)
    else:
        raise PykeError("Unable to find project \"{0}\".".format(t.make_project_name(command.name)))
        
    
def run_pyke_command(command):
    if command.name == "help":
        print_usage()
        
    elif command.name == "list-projects":
        build_in.run_list_projects(command)
        
    else:
        run_project(command)
        

def main(args):
    # parse command line
    commands = None
    should_print_usage = False
    try:
        p = com.parser()
        commands = p.parse_args(args)
    except ValueError as ve:
        print (ve)
        should_print_usage = True
    
    timer.mark("Command line parsing")
    
    # execute commands
    if getattr(commands, "children", None) == None:
        print ("No commands or projects detected.")
        should_print_usage = True
    else:
        for cmd in commands.children:
            try:
                run_pyke_command(cmd)
            except PykeError as pe:
                print (t.make_error("PykeError raised:"))
                print (pe)
    
    if should_print_usage:
        print_usage()
    
    timer.report()

