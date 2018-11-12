import os
import io
import re
import subprocess
from terminal import terminal as t
from error import PykeError
from .tool import tool

class cpp_data:
    def __init__(self, project, json_data):
        self.version = json_data['version']
        self.output_type = json_data['output-type']
        self.use_std = json_data['use-std']
        self.include_dirs = json_data['include-dirs']
        self.use_std_include_dirs = json_data['use-std-include-dirs']
        self.source_dir = json_data['source-dir']
        self.resource_dir = json_data['resource-dir']
        self.lib_dirs = json_data['lib-dirs']
        self.intermediate_dir = json_data['intermediate-dir']
        self.output_dir = json_data['output-dir']
        self.output_name = json_data['output-name']
        self.sources = json_data['sources']
        self.resources = json_data['resources']
        self.packages = json_data['packages']
        self.libs = json_data['libs']
        self.compile_args = json_data['compile-args']
        self.link_args = json_data['link-args']
        self.whole_build_args = json_data['whole-build-args']
        self.multithreaded = json_data['multithreaded']
        self.whole_program = json_data['whole-program']
        self.whole_opt = json_data['whole-opt']
        self.depends_on = project.depends_on
        self.applied_configs = project.applied_configs

class cpp_source:
    def __init__(self, src_entry, path, doto_path, simulate):
        self.simulate = simulate
        self.src_entry = src_entry

        self.src_path = path
        self.src_exists = os.path.exists(self.src_path)
        self.src_mtime = os.path.getmtime(self.src_path) if self.src_exists else 0

        self.doto_path = doto_path
        self.doto_exists = os.path.exists(self.doto_path)
        self.doto_mtime = os.path.getmtime(self.doto_path) if self.doto_exists else 0

        self.is_includes_resolved = False
        self.included_files = []

    def is_up_to_date(self, target_mtime):
        for inc in self.included_files:
            if os.path.getmtime(inc) > target_mtime:
                return False
        
        if self.src_mtime > target_mtime:
            return False
        
        return True


class cpp_tool(tool):
    def __init__(self, json_dir, simulate=False):
        self.path = json_dir
        self.simulate = simulate
  #      self.include_quote_regex = re.compile(r'^\#\s*include\s*\"([A-Za-z0-9_\.\-\(\)\:]+)\".*$')
  #      self.include_angle_regex = re.compile(r'^\#\s*include\s*\<([A-Za-z0-9_\.\-\(\)\:]+)\>.*$')

        self.include_quote_dirs = []
        self.include_angle_dirs = []

        self.resolved_includes = {}
        self.included_files = {}
  #      self._compute_include_search_dirs()

        self.sources = {}
        
        
    def _compute_include_search_dirs(self):
        gcc_cmd = 'g++ -E -Wp,-v -xc++ /dev/null'
#        print (t.make_syscommand(gcc_cmd))
        # run command
        # parse output
        # '#include "..." search starts here:
        # ' dir-preceded-by-space
        # ' dir-preceded-by-space
        # ' dir-preceded-by-space
        # '#include <...> search starts here:
        # ' dir-preceded-by-space
        # ' dir-preceded-by-space
        # ' dir-preceded-by-space
        comp_proc = subprocess.run(gcc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if comp_proc.returncode != 0:
            raise PykeError('Error getting search directories: Running command:\n\"{0}\"\nreturned {1}.'.format(gcc_cmd, comp_proc.returncode))
        
        doing_quote_includes = False
        doing_angle_includes = False
        buf = io.StringIO(comp_proc.stderr.decode('utf-8'))
        for line in buf:
            inc_full_path = ""
            
            if (doing_quote_includes == False and
                doing_angle_includes == False):
                m = self.include_quote_regex.match(line)
                if m:
                    doing_quote_includes = True
                    doing_angle_includes = False

            elif doing_quote_includes == True:
                m = self.include_angle_regex.match(line)
                if m:
                    doing_quote_includes = False
                    doing_angle_includes = True
                elif line[0] == ' ':
                    inc_path = line.strip()
                    inc_full_path = os.path.abspath(inc_path)
            elif doing_angle_includes == True:
                if line[0] == ' ':
                    inc_path = line.strip()
                    inc_full_path = os.path.abspath(inc_path)
                else:
                    doing_angle_includes = False
            
            if inc_full_path != "":
                if doing_quote_includes:
                    self.include_quote_dirs.append(inc_full_path)
                elif doing_angle_includes:
                    self.include_angle_dirs.append(inc_full_path)
                    
#        print ("Quote-dirs:")
#        [print ("  {0}".format(t.make_dir(d))) for d in self.include_quote_dirs]
#        print ("Angle-dirs:")
#        [print ("  {0}".format(t.make_dir(d))) for d in self.include_angle_dirs]
        
    
    def set_cpp_data(self, cpp_data):
        self.cpp_data = cpp_data
        # TODO: apply -iquote dirs to include_quote_dirs
        self.include_angle_dirs = [os.path.join(self.path, d) for d in self.cpp_data.include_dirs] + self.include_angle_dirs

        for src in self.cpp_data.sources:
            src_path = self.make_src_path(src)
            doto_path = self.make_doto_path(src)
            self.sources[src_path] = cpp_source(src, src_path, doto_path, self.simulate)

        self.intermediate_dir = os.path.normpath(os.path.join(self.path, self.cpp_data.intermediate_dir))
        self.output_dir = os.path.normpath(os.path.join(self.path, self.cpp_data.output_dir))
        self.output_path = os.path.normpath(os.path.join(self.output_dir, self._make_output_name()))

    
    def set_is_simulating(self, is_sim):
        self.simulate = is_sim


    def _ensure_dir_exists(self, dirname):
        try:
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        
    
    def _make_output_name(self):
        if self.cpp_data.output_type == "lib":
            return "lib{}.a".format(self.cpp_data.output_name)
            
        elif self.cpp_data.output_type == "so":
            version = self.cpp_data.version.split('.')
            return "lib{0}.so.{1}.{2}".format(
                self.cpp_data.output_name,
                version[0] if len(version) > 0 else 0,
                version[1] if len(version) > 1 else 0)
            
        elif self.cpp_data.output_type == "exe":
            return self.cpp_data.output_name
        else:
            return self.cpp_data.output_name


    def make_src_path(self, src_entry):
        return os.path.normpath(os.path.join(self.path, self.cpp_data.source_dir, src_entry))

    
    def get_doto_entry(self, src_entry):
        base, _ = os.path.splitext(src_entry)
        return ''.join((base, ".o"))
    

    def make_doto_path(self, src_entry):
        base, _ = os.path.splitext(src_entry)
        return os.path.normpath(os.path.join(self.path, self.cpp_data.intermediate_dir, ''.join((base, ".o"))))
        
        
        
        
    def _make_std(self):
        if self.cpp_data.use_std != None:
            return "-std=c++{}".format(self.cpp_data.use_std)
        else:
            return ""
        
    
    def _make_src(self):
        src = [path.src_path for path in self.sources]
#        src = [os.path.join(self.path, self.cpp_data.source_dir, src) for src in self.cpp_data.sources]
        return " ".join(src)


    def _make_include_dirs(self):
        include_dirs = ["-I{}".format(os.path.join(self.path, path)) for path in self.cpp_data.include_dirs]
        return " ".join(include_dirs)
        

    def _make_lib_dirs(self):
        # making a unique, ordered set
        dirs = set()
        lib_dirs = []
        
        for _, p in self.cpp_data.depends_on.items():
            d = os.path.dirname(p.tool.get_output_path())
            if d not in dirs:
                dirs.add(d)
                lib_dirs.append(d)
            
        for d in self.cpp_data.lib_dirs:
            d = os.path.join(self.path, d)
            if d not in dirs:
                dirs.add(d)
                lib_dirs.append(d)
            
        lib_dirs = ["-L{}".format(d) for d in lib_dirs]
        return " ".join(lib_dirs)


    def _make_libs(self):
        libs = ["-l{}".format(path) for path in self.cpp_data.libs]
        return " ".join(libs)
    

    def _make_dotos(self):
        objs = [self.make_doto_path(src) for src in self.cpp_data.sources]
        return ' '.join(objs)
        
        
    def _make_package_includes(self):
        packages = self.cpp_data.packages
        if len(packages) > 0:
            return "`pkg-config --cflags {}`".format(" ".join(packages))
        else:
            return ""
    
    
    def _make_package_libs(self):
        packages = self.cpp_data.packages
        if len(packages) > 0:
            return "`pkg-config --libs {}`".format(" ".join(packages))
        else:
            return ""
            

    def _resolve_includes(self, src_path):
        cpp_cmd = "cpp -M {std} {includes} {packages} {src}".format(
            std = self._make_std(),
            includes = self._make_include_dirs(),
            packages = self._make_package_includes(),
            src = src_path)
        print (t.make_syscommand(cpp_cmd))
        comp_proc = subprocess.run(cpp_cmd, input='', 
            stdout=subprocess.PIPE, shell=True, universal_newlines=True)            
        if comp_proc.returncode != 0:
            self.sources[src_path].is_includes_resolved = False
            raise PykeError('{0} resolving #includes for {1}'.format(
                t.make_error('Error'),
                t.make_file_name(src_path)))

        self.sources[src_path].is_includes_resolved = True
        self.sources[src_path].included_files = [f for d in comp_proc.stdout.splitlines()[1:]    # each line of input can have n paths
        for f in str(d).rstrip(" \\").split()]        # clean and split each line to list paths


    def _validate_src(self, src_entry):
        src = self.make_src_path(src_entry)
        print ("Validating {0}:".format(
            t.make_file_name(src)))
        self._resolve_includes(src)
        if not self.sources[src].is_includes_resolved:
            raise PykeError("{0} has #include paths that cannot be resolved.".format(
                t.make_file_name(src_entry)))
        

    def _build_all_objects(self, force=False):
        fail = False
        for _, source in self.sources.items():
            try:
                self._build_object(source.src_path, force)
            except PykeError as pe:
                print (t.make_error("PykeError raised:"))
                print (pe)
                fail = True
        if fail:
            raise PykeError("One or more objects failed to build.")
    

    def _build_object(self, src_path, force=False):
        source = self.sources[src_path]
        doto_dir, doto_file = os.path.split(source.doto_path)
        
        print ()
        title_bw = "Building {}".format(doto_file)
        title_co = "Building {}".format(t.make_file_name(doto_file))
        t.print_title(title_co, len(title_bw))

        src_entry = self.sources[src_path].src_entry
        if not os.path.exists(src_path):
            raise PykeError("{0} not found".format(
                t.make_file_name(src_path)))

        self._validate_src(src_path)
        
        self._ensure_dir_exists(doto_dir)

        if (force or
            not os.path.exists(source.doto_path) or
            not source.is_up_to_date(source.doto_mtime)):

            include_dirs = self._make_include_dirs()
            config = self.cpp_data.compile_args
            if self.cpp_data.output_type == 'so':
                config = ''.join((config, ' -fPIC'))
            
            if os.path.exists(source.doto_path):
                os.remove(source.doto_path)
            
            gcc_cmd = "g++ {std} -c {config} {src} {includes} {packages} -o {doto}".format(
                std = self._make_std(),
                packages = self._make_package_includes(),
                config = config,
                includes = include_dirs,
                src = src_path,
                doto = source.doto_path)

            print (t.make_syscommand(gcc_cmd))
            comp_proc = subprocess.run(gcc_cmd, stdout=subprocess.PIPE, shell=True)
            if comp_proc.returncode != 0:
                raise PykeError('{0} building {1}'.format(
                    t.make_error('Error'),
                    t.make_file_name(source.doto_path)))
            else:
                print ("{0} built {1}.".format(
                    t.make_file_name(source.doto_path),
                    t.make_success('successfully')))
            
        else:
            print ("{0} is up to date.".format(
                t.make_file_name(source.doto_path)))
                
    
    def _link_objects(self, force=False):
        print ()
        output_dir, output_name = os.path.split(self.output_path)
        
        title_bw = "Building {}".format(output_name)
        title_co = "Building {}".format(t.make_file_name(output_name))
        t.print_title(title_co, len(title_bw))

        self._ensure_dir_exists(output_dir)

        if self.cpp_data.output_type == "lib":
            gcc_cmd = "ar cvq -o {outfile} {objs}".format(
                outfile = self.output_path,
                objs = self._make_dotos())
            
        elif self.cpp_data.output_type == "so":
            _, soname = os.path.split(self.output_path)
            soname = soname[0:soname.rindex('.')]
            gcc_cmd = "g++ {std} -shared -Wl,-soname,{name} {config} -o {outfile} {objs} {packages} {libs} {libdirs}".format(
                std = self._make_std(),
                name = soname,
                config = self.cpp_data.link_args,
                outfile = self.output_path,
                objs = self._make_dotos(),
                packages = self._make_package_libs(),
                libs = self._make_libs(),
                libdirs = self._make_lib_dirs())
        
        elif self.cpp_data.output_type == "exe":
            gcc_cmd = "g++ {std} {config} -o {outfile} {objs} {libdirs} {libs} {packages}".format(
                std = self._make_std(),
                config = self.cpp_data.link_args,
                outfile = self.output_path,
                objs = self._make_dotos(),
                libs = self._make_libs(),
                libdirs = self._make_lib_dirs(),
                packages = self._make_package_libs())
        
        objs = [self.make_doto_path(src) for src in self.cpp_data.sources]
        newest_obj_time = max([os.path.getmtime(obj) for obj in objs])
        
        project_deps = [p.tool.get_output_path() for _, p in self.cpp_data.depends_on.items()]
        if len(project_deps) > 0:
            newest_obj_time = max(newest_obj_time, max([os.path.getmtime(p) for p in project_deps]))
        
        if (force or
            not os.path.exists(self.output_path) or
            newest_obj_time > os.path.getmtime(self.output_path)):

            if os.path.exists(self.output_path):
                os.remove(self.output_path)
        
            print (t.make_syscommand(gcc_cmd))
            comp_proc = subprocess.run(gcc_cmd, stdout=subprocess.PIPE, shell=True)
            if comp_proc.returncode != 0:
                raise PykeError('{0} linking {1}'.format(
                    t.make_error('Error'),
                    t.make_file_name(self.output_path)))
            else:
                print ("{0} linked {1}.".format(
                    t.make_file_name(self.output_path),
                    t.make_success('successfully')))
        else:
            print ("{0} is up to date.".format(
                t.make_file_name(self.output_path)))


    def _build_so_links(self, force=False):
        mod_name = self.output_path[0:self.output_path.rindex('.')]
        if not os.path.lexists(mod_name):
            print ("Making soft link {}".format(t.make_file_name(mod_name)))
            os.unlink(mod_name)
            os.symlink(self.output_path, mod_name)
        else:
            print ("{} is up to date.".format(
                t.make_file_name(mod_name)))
            
        mod_name = mod_name[0:mod_name.rindex('.')]
        if not os.path.lexists(mod_name):
            print ("Making soft link {}".format(t.make_file_name(mod_name)))
            os.unlink(mod_name)
            os.symlink(self.output_path, mod_name)
        else:
            print ("{} is up to date.".format(
                t.make_file_name(mod_name)))

    
    def _build_lib(self, force=False):
        output_dir = os.path.dirname(self.output_path)
        self._ensure_dir_exists(output_dir)
        
        if self.cpp_data.whole_program:
            gcc_cmd = "g++ {std} -c {wholeBuildArgs} {packageIncludes} {includeDirs} -o {outfile} {src} {libs} {libdirs} {packageLinks}".format(
            
                std = self._make_std(),
                wholeBuildArgs = self.cpp_data.whole_build_args,
                packageIncludes = self._make_package_includes(),
                includeDirs = self._make_include_dirs(),
                outfile = self.output_path,
                src = self._make_src(),
                libs = self._make_libs(),
                libdirs = self._make_lib_dirs(),
                packages = self._make_package_libs())
            
            print (gcc_cmd)
        else:
            self._build_all_objects(force)
            self._link_objects(force)
        
    
    def _build_so(self, force=False):
        output_dir = os.path.dirname(self.output_path)
        self._ensure_dir_exists(output_dir)
        
        if self.cpp_data.whole_program:
            gcc_cmd = "g++ {std} -shared -Wl,-soname,{name} -c -fPIC {wholeBuildArgs} {packageIncludes} {includeDirs} -o {outfile} {src} {libs} {libdirs} {packageLinks}".format(
            
                std = self._make_std(),
                name = self.cpp_data.output_name,
                wholeBuildArgs = self.cpp_data.whole_build_args,
                packageIncludes = self._make_package_includes(),
                includeDirs = self._make_include_dirs(),
                outfile = self.output_path,
                src = self._make_src(),
                libs = self._make_libs(),
                libdirs = self._make_lib_dirs(),
                packages = self._make_package_libs())
            
            print (gcc_cmd)
        else:
            self._build_all_objects(force)
            self._link_objects(force)
        
        self._build_so_links(force)
        
    
    def _build_exe(self, force=False):
        output_dir = os.path.dirname(self.output_path)
        self._ensure_dir_exists(output_dir)

        if self.cpp_data.whole_program:
            gcc_cmd = "g++ {std} -c {wholeBuildArgs} {packageIncludes} {includeDirs} -o {outfile} {src} {libs} {libdirs} {packageLinks}".format(
            
                std = self._make_std(),
                wholeBuildArgs = self.cpp_data.whole_build_args,
                packageIncludes = self._make_package_includes(),
                includeDirs = self._make_include_dirs(),
                outfile = self.self.output_path,
                src = self._make_src(),
                libs = self._make_libs(),
                libdirs = self._make_lib_dirs(),
                packages = self._make_package_libs())
            
            print (gcc_cmd)
        else:
            self._build_all_objects(force)
            self._link_objects(force)
        
        self._build_run_script()
    
    
    # TODO: Move this into a shell-specific tool.
    # TODO: Dependent projects need not be C++, long as they shit out a .so.
    def _build_run_script(self):
        dep_p = [p for _, p in self.cpp_data.depends_on.items()]
        dep_d = [os.path.dirname(p.tool.get_output_path()) for p in dep_p if p.tool.cpp_data.output_type == 'so']
        sodirs = ';'.join(dep_d)

        def write_script(debug):
            debug_mark = ''
            debug_cmd = ''

            if debug:
                debug_mark = '.d'
                debug_cmd = 'gdb '

            script_path = os.path.join(self.path, 'run.{}{}.sh'.format(
                os.path.basename(self.output_path), 
                debug_mark))
            print ("Making run script {}".format(t.make_file_name(script_path)))
            
            try:
                with open(script_path, 'w') as f:
                    output_dir = os.path.dirname(self.output_path)
                    if len(dep_d) > 0:
                        f.write('export LD_LIBRARY_PATH="$LD_LIBRARY_PATH;{}"\n'.format(sodirs))
                    if debug:
                        f.write('{}{} "$@"\n'.format(debug_cmd, self.output_path))
                    else:
                        f.write('{} "$@"\n'.format(self.output_path))
            except IOError as e:
                raise PykeError(e)
                
            try:
                os.chmod(script_path, 0o755)
            except OSError as e:
                raise PykeError(e)

        debug = False
        for config in self.cpp_data.applied_configs:
            if config == 'debug':
                debug = True
            elif config == 'release':
                debug = False

        write_script(debug)


    def is_up_to_date(self):
        for src in self.cpp_data.sources:
            full_src = self.make_src_path(src)
            src_mtime = os.path.get_mtime(full_src)
            try:
                self._resolve_includes(full_src)
                doto_path = self.make_doto_path(src)
                doto_mtime = 0.0
                ouput_path = self.get_output_path()
                output_mtime = 0.0

                if os.path.exists(doto_path):
                    doto_mtime = os.path.getmtime(doto_path)

                if os.path.exists(output_path):
                    output_mtime = os.path.getmtime(output_path)

                comparator = doto_mtime
                if self.cpp_data.whole_program:
                    comparator = outut_mtime

                # If any include files are newer than the doto, we need to build.
                for incf in self.included_files[full_src]:
                    if os.path.get_mtime(incf) > comparator:
                        print ("{0} is out of date by {1} (and possibly others).".format(
                            t.make_file_name(src), t.make_file_name(incf)))
                        return False
                
                if self.cpp_data.whole_program:
                    if src_mtime > output_mtime:
                        print ("{0} is out of date by {1}.".format(
                            t.make_file_name(src), t.make_file_name(output_path)))
                        return False
                else:
                    if src_mtime > doto_mtime:
                        print ("{0} is out of date by {1}.".format(
                            t.make_file_name(doto_path), t.make_file_name(full_src)))
                        return False
                        
                    if doto_mtime > output_mtime:
                        print ("{0} is out of date by {1}.".format(
                            t.make_file_name(output_path), t.make_file_name(doto_path)))
                        return False
                
            except IOError as e:
                print ("{0}: {1}".format(
                    t.make_error('Error'), e))
                return False
        
        return True
        

    def clean_project(self):
        print ("Cleaning object files from {}:".format(
            t.make_dir(self.get_intermediate_dir())))
        for source in self.sources:
            if source.doto_exists:
                print ("\tCleaning {0}".format(t.make_file_name(source.doto_path)))
                os.remove(source.doto_path)
        
        print ("Cleaning target files from {}:".format(
            t.make_dir(self.output_dir)))
        if os.path.exists(self.output_path):
            print ("\tCleaning {0}".format(os.path.basename(self.output_path)))
            os.remove(self.output_path)
    
        if self.cpp_data.output_type == "so":
            mod_name = self.output_path[0:self.output_path.rindex('.')]
            if os.path.lexists(mod_name):
                print ("\tCleaning {}".format(mod_name))
                os.unlink(mod_name)
            mod_name = mod_name[0:mod_name.rindex('.')]
            if os.path.lexists(mod_name):
                print ("\tCleaning {}".format(mod_name))
                os.unlink(mod_name)


    def build_project(self, force=False):
        if self.cpp_data.output_type == "lib":
            self._build_lib()
        elif self.cpp_data.output_type == "so":
            self._build_so()
        elif self.cpp_data.output_type == "exe":
            self._build_exe()

    

