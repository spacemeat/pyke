import os
import io
import re
import subprocess
from terminal import terminal as t
from error import PykeError
from .tool import tool

class cpp_data:
    def __init__(self, project, json_data, configuration = None):
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
        

class cpp_tool(tool):
    def __init__(self, json_dir, simulate=False):
        self.path = json_dir
        self.simulate = simulate
        self.include_quote_regex = re.compile(r'^\#\s*include\s*\"([A-Za-z0-9_\.\-\(\)\:]+)\".*$')
        self.include_angle_regex = re.compile(r'^\#\s*include\s*\<([A-Za-z0-9_\.\-\(\)\:]+)\>.*$')

        self.include_quote_dirs = []
        self.include_angle_dirs = []
        self._compute_include_search_dirs()
        
        
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

    
    def set_is_simulating(self, is_sim):
        self.simulate = is_sim


    def _ensure_dir_exists(self, dirname):
        try:
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        
    
    def get_output_name(self):
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


    def get_src_path(self, src_entry):
        return os.path.join(self.path, self.cpp_data.source_dir, src_entry)

    
    def get_doto_subpath(self, src_entry):
        base, _ = os.path.splitext(src_entry)
        return ''.join((base, ".o"))
    

    def get_doto_path(self, src_entry):
        base, _ = os.path.splitext(src_entry)
        return os.path.join(self.path, self.cpp_data.intermediate_dir, ''.join((base, ".o")))
        
        
    def get_intermediate_dir(self):
        return os.path.join(self.path, self.cpp_data.intermediate_dir)
        
        
    def get_output_path(self):
        return os.path.join(self.path, self.cpp_data.output_dir, self.get_output_name())
        
        
    def _make_std(self):
        if self.cpp_data.use_std != None:
            return "-std=c++{}".format(self.cpp_data.use_std)
        else:
            return ""
        
    
    def _make_src(self):
        src = [os.path.join(self.path, self.cpp_data.source_dir, src) for src in self.cpp_data.sources]
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
        objs = [self.get_doto_path(src) for src in self.cpp_data.sources]
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
        resolved = []
        unresolved = []
        # NOTE: See https://gcc.gnu.org/onlinedocs/gcc/Directory-Options.html
        # for a description of all the gcc include dir flags (-I, -iquote, etc)
        qdirs = [os.path.dirname(src_path)]
        qdirs.extend(self.include_quote_dirs)
        
        def search_angle_dirs(inc_path, quote=False):
            for base in self.include_angle_dirs:
                full_path = os.path.join(base, inc_path)
                if os.path.exists(full_path):
                    resolved.append((inc_path, quote, full_path))
                    return
            unresolved.append(inc_path)

        def search_quote_dirs(inc_path):
            for base in qdirs:
                full_path = os.path.join(base, inc_path)
                if os.path.exists(full_path):
                    resolved.append((inc_path, True, full_path))
                    return
            search_angle_dirs(inc_path, quote=True)
    
        with open(src_path) as f:
            for line in f:
                inc_full_path = ""
                m = self.include_quote_regex.match(line)
                if m:
                    inc_path = m.group(1)
                    search_quote_dirs(inc_path)
                else:
                    m = self.include_angle_regex.match(line)
                    if m:
                        inc_path = m.group(1)
                        search_angle_dirs(inc_path)
            
        return (resolved, unresolved)


    def _validate_src(self, src_entry):
        src = self.get_src_path(src_entry)
        print ("Validating {0}:".format(
            t.make_file_name(src)))
        res, unres = self._resolve_includes(src)
        for dirr in res:
            print ("{0} found at {1}".format(
                t.make_include(dirr[0]), 
                t.make_file_name(dirr[2])))
        for dirr in unres:
            print ("{0} not found.".format(
                t.make_include(dirr)))
        if len(unres) > 0:
            raise PykeError("{0} failed validation.".format(
                t.make_file_name(src_entry)))
        return (res, unres)
        

    def _build_all_objects(self, force=False):
        fail = False
        for src in self.cpp_data.sources:
            try:
                self._build_object(src, force)
            except PykeError as pe:
                print (t.make_error("PykeError raised:"))
                print (pe)
                fail = True
        
        if fail:
            raise PykeError("One or more objects failed to build.")
    

    def _build_object(self, src_entry, force=False):
        doto = self.get_doto_path(src_entry)
        doto_dir, doto_file = os.path.split(doto)
        
        print ()
        title_bw = "Building {}".format(doto_file)
        title_co = "Building {}".format(t.make_file_name(doto_file))
        t.print_title(title_co, len(title_bw))

        src = self.get_src_path(src_entry)
        if not os.path.exists(src):
            raise PykeError("{0} not found".format(
                t.make_file_name(src)))

        # Check for mtimes of include deps
        deps_are_newer = False
        res, unres = self._validate_src(src_entry)
        
        self._ensure_dir_exists(doto_dir)

        if os.path.exists(doto):
            doto_mtime = os.path.getmtime(doto)
            for filee in (f[2] for f in res if f[1]):
                if os.path.getmtime(filee) > doto_mtime:
                    deps_are_newer = True
        
        if (force or
            deps_are_newer or
            not os.path.exists(doto) or
            os.path.getmtime(src) > os.path.getmtime(doto)):

            include_dirs = self._make_include_dirs()
            config = self.cpp_data.compile_args
            if self.cpp_data.output_type == 'so':
                config = ''.join((config, ' -fPIC'))
            
            gcc_cmd = "g++ {std} -c {config} {src} {includes} {packages} -o {doto}".format(
                std = self._make_std(),
                packages = self._make_package_includes(),
                config = config,
                includes = include_dirs,
                src = src,
                doto = doto)

            if os.path.exists(doto):
                os.remove(doto)
            
            print (t.make_syscommand(gcc_cmd))
            comp_proc = subprocess.run(gcc_cmd, stdout=subprocess.PIPE, shell=True)
            if comp_proc.returncode != 0:
                raise PykeError('{0} building {1}'.format(
                    t.make_error('Error'),
                    t.make_file_name(doto)))
            else:
                print ("{0} built {1}.".format(
                    t.make_file_name(doto),
                    t.make_success('successfully')))
            
        else:
            print ("{0} is up to date.".format(
                t.make_file_name(doto)))
                
    
    def _link_objects(self, force=False):
        print ()
        output_path = self.get_output_path()
        output_dir, output_name = os.path.split(output_path)
        
        title_bw = "Building {}".format(output_name)
        title_co = "Building {}".format(t.make_file_name(output_name))
        t.print_title(title_co, len(title_bw))

        self._ensure_dir_exists(output_dir)

        if self.cpp_data.output_type == "lib":
            gcc_cmd = "ar cvq -o {outfile} {objs}".format(
                outfile = output_path,
                objs = self._make_dotos())
            
        elif self.cpp_data.output_type == "so":
            _, soname = os.path.split(output_path)
            soname = soname[0:soname.rindex('.')]
            gcc_cmd = "g++ {std} -shared -Wl,-soname,{name} {config} -o {outfile} {objs} {packages} {libs} {libdirs}".format(
                std = self._make_std(),
                name = soname,
                config = self.cpp_data.link_args,
                outfile = output_path,
                objs = self._make_dotos(),
                packages = self._make_package_libs(),
                libs = self._make_libs(),
                libdirs = self._make_lib_dirs())
        
        elif self.cpp_data.output_type == "exe":
            gcc_cmd = "g++ {std} {config} -o {outfile} {objs} {libdirs} {libs} {packages}".format(
                std = self._make_std(),
                config = self.cpp_data.link_args,
                outfile = output_path,
                objs = self._make_dotos(),
                libs = self._make_libs(),
                libdirs = self._make_lib_dirs(),
                packages = self._make_package_libs())
        
        objs = [self.get_doto_path(src) for src in self.cpp_data.sources]
        newest_obj_time = max([os.path.getmtime(obj) for obj in objs])
        
        project_deps = [p.tool.get_output_path() for _, p in self.cpp_data.depends_on.items()]
        if len(project_deps) > 0:
            newest_obj_time = max(newest_obj_time, max([os.path.getmtime(p) for p in project_deps]))
        
        if (force or
            not os.path.exists(output_path) or
            newest_obj_time > os.path.getmtime(output_path)):

            if os.path.exists(output_path):
                os.remove(output_path)
        
            print (t.make_syscommand(gcc_cmd))
            comp_proc = subprocess.run(gcc_cmd, stdout=subprocess.PIPE, shell=True)
            if comp_proc.returncode != 0:
                raise PykeError('{0} linking {1}'.format(
                    t.make_error('Error'),
                    t.make_file_name(output_path)))
            else:
                print ("{0} linked {1}.".format(
                    t.make_file_name(output_path),
                    t.make_success('successfully')))
        else:
            print ("{0} is up to date.".format(
                t.make_file_name(output_path)))


    def _build_so_links(self, force=False):
        output_path = self.get_output_path()
        mod_name = output_path[0:output_path.rindex('.')]
        if not os.path.lexists(mod_name):
            print ("Making soft link {}".format(t.make_file_name(mod_name)))
            os.unlink(mod_name)
            os.symlink(output_path, mod_name)
        else:
            print ("{} is up to date.".format(
                t.make_file_name(mod_name)))
            
        mod_name = mod_name[0:mod_name.rindex('.')]
        if not os.path.lexists(mod_name):
            print ("Making soft link {}".format(t.make_file_name(mod_name)))
            os.unlink(mod_name)
            os.symlink(output_path, mod_name)
        else:
            print ("{} is up to date.".format(
                t.make_file_name(mod_name)))

    
    def _build_lib(self, force=False):
        output_path = self.get_output_path()
        output_dir = os.path.dirname(output_path)
        self._ensure_dir_exists(output_dir)
        
        if self.cpp_data.whole_program:
            gcc_cmd = "g++ {std} -c {wholeBuildArgs} {packageIncludes} {includeDirs} -o {outfile} {src} {libs} {libdirs} {packageLinks}".format(
            
                std = self._make_std(),
                wholeBuildArgs = self.cpp_data.whole_build_args,
                packageIncludes = self._make_package_includes(),
                includeDirs = self._make_include_dirs(),
                outfile = output_path,
                src = self._make_src(),
                libs = self._make_libs(),
                libdirs = self._make_lib_dirs(),
                packages = self._make_package_libs())
            
            print (gcc_cmd)
        else:
            self._build_all_objects(force)
            self._link_objects(force)
        
    
    def _build_so(self, force=False):
        output_path = self.get_output_path()
        output_dir = os.path.dirname(output_path)
        self._ensure_dir_exists(output_dir)
        
        if self.cpp_data.whole_program:
            gcc_cmd = "g++ {std} -shared -Wl,-soname,{name} -c -fPIC {wholeBuildArgs} {packageIncludes} {includeDirs} -o {outfile} {src} {libs} {libdirs} {packageLinks}".format(
            
                std = self._make_std(),
                name = self.cpp_data.output_name,
                wholeBuildArgs = self.cpp_data.whole_build_args,
                packageIncludes = self._make_package_includes(),
                includeDirs = self._make_include_dirs(),
                outfile = output_path,
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
        output_path = self.get_output_path()
        output_dir = os.path.dirname(output_path)
        self._ensure_dir_exists(output_dir)

        if self.cpp_data.whole_program:
            gcc_cmd = "g++ {std} -c {wholeBuildArgs} {packageIncludes} {includeDirs} -o {outfile} {src} {libs} {libdirs} {packageLinks}".format(
            
                std = self._make_std(),
                wholeBuildArgs = self.cpp_data.whole_build_args,
                packageIncludes = self._make_package_includes(),
                includeDirs = self._make_include_dirs(),
                outfile = output_path,
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
        
        script_path = os.path.join(self.path, 'run.sh')
        print ("Making run script {}".format(t.make_file_name(script_path)))
        
        try:
            with open(script_path, 'w') as f:
                output_path = self.get_output_path()
                output_dir = os.path.dirname(output_path)
                if len(dep_d) > 0:
                    f.write('export LD_LIBRARY_PATH="$LD_LIBRARY_PATH;{}"\n'.format(sodirs))
                f.write('{}\n'.format(output_path))
        except IOError as e:
            raise PykeError(e)
            
        try:
            os.chmod(script_path, 0o755)
        except OSError as e:
            raise PykeError(e)


    def is_up_to_date(self):
        for src in self.cpp_data.sources:
            full_src = self.get_src_path(src)
            src_mtime = os.path.get_mtime(full_src)
            try:
                res, unres = self._resolve_includes(full_src)
                # res contains [(label, quote, path),...]
                # unres contains [label, ...]
                for incf in res:
                    if os.path.get_mtime(incf[2]) > src_mtime:
                        return False
                
                if self.cpp_data.whole_program:
                    output_mtime = os.path.getmtime(self.get_output_path())
                    if src_mtime > output_mtime:
                        return False
                else:
                    doto = self.get_doto_path(src)
                    doto_mtime = os.path.getmtime(doto)
                    if src_mtime > doto_mtime:
                        return False
                        
                    if doto_mtime > os.path.getmtime(self.get_output_path()):
                        return False
                
            except IOError as e:
                print ("{0}: {1}".format(
                    t.make_error('Error'), e))
                return False
        
        return True
        

    def clean_project(self):
        print ("Cleaning object files from {}:".format(
            t.make_dir(self.get_intermediate_dir())))
        for src in self.cpp_data.sources:
            obj_path = self.get_doto_path(src)
            if os.path.exists(obj_path):
                print ("\tCleaning {0}".format(self.get_doto_subpath(src)))
                os.remove(obj_path)
        
        output_dir = os.path.join(self.path, self.cpp_data.output_dir)
        print ("Cleaning target files from {}:".format(
            t.make_dir(output_dir)))
        output_name = self.get_output_name()
        output_path = os.path.join(self.path, self.cpp_data.output_dir, output_name)
        if os.path.exists(output_path):
            print ("\tCleaning {0}".format(output_name))
            os.remove(output_path)
    
        if self.cpp_data.output_type == "so":
            mod_name = output_path[0:output_path.rindex('.')]
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

    

