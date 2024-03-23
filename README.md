# pyke

Pyke is a python-based, extensible system for building and operating software projects. Its first functions centered around cleaning and building C and C++ projects, but it can do much more. Future development work will expand languages and environments in which pyke can be useful, actions such as running, installing, deploying and testing, and will support a plugin interface for expansion beyond the core.

## The rationale

Pyke is being designed to act initially as an alternative to CMake. I'm not expert in CMake, and many of the below may also apply to it, but I wanted to build pyke as a personal project, and use it in other projects of my own.

- **Minimal artifacts**
Within a project, the only artifacts that result from a build operation are the intermediate files from the build itself (.o files, specifically, for C-family projects) and the final output. The only necessary support file in a project is the make.py file itself, probably at the project root folder.

- **Flexibility**
Of course, the pyke project file doesn't have to be at the root of a project. And it doesn't have to be called make.py. A pyke file can specify specific anchor directories for project files and generated artifacts. Command-line overrides can modify them in times of need.

- **Just-beyond-declarative configuration**
Usually, a declarative syntax is desireable for systems like this. But even CMake is a sort of language, and pyke files are too--just, in python. Very basic python is all you need to know to use it fully, and when you need that convenience of a full language, it's very nice to have. Sane defaults and a simple object structure help keep things fairly minimal for a basic project.

- **Extensibility**
Pyke comes with some basic classes (called `Phase`s) which can manage basic tasks. But you may have special needs in your project tha require a specific tool to be run, or files to be moved around, or secret keys to be managed, etc. If it's not in the basic set of classes, build your own. It's a reasonable interface to design new functionality for.

Eventually there will be a plugin interface for separate extension projects. This is still being designed, and the basic builtin classes are being fleshed out now.

## Installing pyke

Pyke is very nearly ready for its first submission to PyPI. Until then, clone this repo and install locally:

```
$ git clone git@github.com:spacemeat/pyke
$ cd pyke
$ pip install .
```
<!--
Couldn't be easier. You need to be running python3.10 at least, and have pip installed. To install it globally:

```
$ pip install pyke
```
or,
```
$ pip install --user pyke
```
-->
You can optionally put it in a virtual environment, which may be the better idea.

## Using pyke

We'll do a simple example. We have a C project laid out like this:

```
simple_app
├── include
│   └── abc.h
└── src
    ├── a.c
    ├── b.c
    ├── c.c
    └── main.c
```

We want to build each .c file to an object, and link the objects together. Let's make a file called make.py, and place it in the root. 

```python
import pyke as p

phase = p.CompileAndLinkPhase({
    'name': 'simple',
    'sources': ['a.cpp', 'b.cpp', 'c.cpp', 'main.cpp'],
    'exe_basename': '{name}',
})

p.main_project().set_dependency(phase)
```

Now it's as simple as invoking pyke:

```
$ pyke build
```

The project was quietly built in a subdirectory:

```
├── build
│   └── release.gnu
│       ├── bin
│       │   └── simple
│       └── int
│           ├── a.o
│           ├── b.o
│           ├── c.o
│           └── main.o
├── include
│   └── abc.h
├── make.py
└── src
    ├── a.cpp
    ├── b.cpp
    ├── c.cpp
    └── main.c
```

where `build/release.gnu/bin/simple` is the final binary executable.

Of course, this is a very minimal example, and much more configuration is possible. 

## The `make.py` file

So what's in this `make.py` file? The general execution is to start pyke, and pyke will then find your `make.py` makefile in the current directory (your project root). Pyke will import the makefile, run it, and then begin executing actions based on what your makefile has configured. All `make.py` does, in the simple cases, is add `Phase`-derived objecs to a provided top-level object. Pyke does the rest.

So in the example above, first `make.py` imports the important pyke symbols. Then it sets up a single phase: `CompileAndLinkPhase`. In its definiton are three `option`s: One sets the name of the phase (not strictly necessary, but good practice as it can be handy), one specifies the C++ sources, and one sets the name of the resulting executable binary file based on the phase's name ("simple" in this case; more on how `{string}`s are interpolated below).

Pyke begins with another phase object (a ProjectPhase instance), for the whole project. It can be accessed through `p.main_project()`, which returns the phase. The CompileAndLinkPhase is then registered to the project via the `set_dependency()` method. Pyke will use the phases it's given, along with the command line arguments, to perform the needed tasks: In this example, it will make the appropriate directories, invoke gcc or clang with configured arguments (in a POSIX environment), and optionally report its progress.

### So how does pyke know where to find the sources? Or the headers?

Every `Phase`-derived class defines its own default options, which give a default configuration for its actions. As an example, one option in `CompileAndLinkPhase` is `src_dir`, which specifies the directory relative to the project root (actually an achor directory, but mnore on that later) where source files can be located. The default is "src", which also happens to be where `simple`'s source files are stored. Similarly, `simple`'s headers are stored in "include", and `CompileAndLinkPhase` has another option named `include_dirs` which contains "[include]". Note that this is a `list` of length one, holding the default directory where include files are to be found. When it comes time to build with, say, `gcc`, the `include_dirs` value becomes "-Iinclude", and the source files are given as source arguments to `gcc`. There is more to the story of how directories are determined, but this suffices for the moment.

Every option can have its default value modified or replaced. If your source files are stored in a different directory (say, "source" instead of "src"), you can add `'src_dir': 'source'` to the phase definition, and pyke will find the files.

> You can also set `src_dir` to "'.'", the dot directory, and explicitly path each source file, like:
> `"'sources': ['src/a.c', 'src/b.c', 'src/c.c', 'src/main.c']"`
> Though, of course, that's just more typing.

### Interpolation, basically

In a nutshell, a string value in an option can have all or part of it enclosed in `{}`. This specifies an interpolation, which is simply to replace that portion of the string with the option given by the name in braces. The name is recursively looked up in the options table, its string values interpolated the same way, and returned to replace. Above, the executable name ("'exe_basename'") is interpolated as "'{name}'". The text is replaced by "simple", the value of the `name` option.

> It should be noted that most of these options so far are actually contained in a `Phase`-derived class called `CFamilyBuildPhase`, which `CompileAndLinkPhase` derives from. This is because several other `CFamilyBuildPhase`-derived classes make use of the same options. It works just the same, as derived phase class inherit their supers' options.

## Phases

Most phases generally represent the transformation of files--inputs to outputs. Any useful build phase will have input files and output files. Some of these may be source, authored by developers. Some may be created by compiling source to objects, linking objects to executables or libraries, cloning repos, or running code generation tools. When the outputs of one phase are the inputs of another, the one is a `dependency` of the other. Dependencies are set in the makefile explicitly, and their output->input mechanistry is automatic once set.

A specific project phase or build phase may be invoked on the command line with `-p <phase-name>`, referencing the `name` of the phase, but this is optional. If a phase is not specified, then the main project phase is used. More on the command line and the -p option later.

Each operation of a build, such as the compilation of a single source file, may have a dedicated phase. C/C++ builds that are more complex than `simple` above are likely to have a `CompilePhase` instance dedicated to each single source file->object file transformation, and one for each link operation, etc. Phases can be cloned, and their options as set at the time of cloning are copied with them. So, a template `CompilePhase` can be preset, and each clone made have its requisite source file set to `src`. Each `CompilePhase` object would then be set as a dependency of a `LinkPhase` object, which will automatically gather the generated object files from each `CompilePhase` for linking. Such an example makefile might look like this (with an additional few source files in a differnt directory, for spice):

```python
'''multiphase cloned simple'''

import pyke as p

c_to_o_phases = []

proto = p.CompilePhase({})

for src in ('a.cpp', 'b.cpp', 'c.cpp', 'main.cpp'):
    c_to_o_phases.append(proto.clone({'name': f'compile_{src}', 'sources': [src]}))

proto = p.CompilePhase({
    'src_dir': 'exp',
    'obj_dir': 'int/exp',
})

for src in ('a.cpp', 'b.cpp'):
    c_to_o_phases.append(proto.clone({'name': f'compile_{src}', 'sources': [src]}))

o_to_exe_phase = p.LinkPhase({
    'name': 'sample',
    'exe_basename': '{name}',
}, c_to_o_phases)

p.main_project().set_dependency(o_to_exe_phase)
```

Here, we're creating a prototype `CompilePhase` object, and storing clones of it, one for each compile operation, in a list. Those phases become dependencies of the `LinkPhase` object, which in turn is set to the main project phase.

### Built-in phases

Pyke comes with some built-in `Phase` classes--not many yet, but it's early still:
* `class Phase`: Common base class for all other phases.
* `class CFamilyBuildPhase(Phase)`: Common base class for building C and C++ projects. You won't decleare objecs of this type, but rather subclasses of it, as it does not actually implement `action`s.
* `class CompilePhase(CFamilyBuildPhase)`: Phase for compiling a single source file to a single object file.
* `class LinkPhase(CFamilyBuildPhase)`: Phase for linking objects together to form <!-- a final archive, shared object, or --> an executable binary.
* `class CompileAndLinkPhase(CFamilyBuildPhase)`: Phase for combining compile and link operations into one phase, likely with a single call to the native build tool.
* `class ProjectPhase(Phase)`: Project phase, which represents a full project. You can create multiple projects as dependencies of `main_project()`, each their own subproject with compile and link phases, etc.

An easier view of the class heierarchy:
```
Phase
├── CFamilyBuildPhase
│   ├── CompilePhase
│   ├── LinkPHase
│   └── CompileAndLinkPhase
├── ProjectPhase
```

### Dependencies

As mentioned, dependencies among phases are set in the makefile. There are several things to know about dependency relationships:
* They cannot be cyclical. The dependency graph must not contain loops, though diamond relationships are fine. (Common dependent phase instances will only perform a particular action once.)
* When options are set to a project phase, they override already-set options in that phase, *and all the dependent phases within that project as well*. This enables one to set an option such as `'kind': 'debug'` in the main project phase, and that override will propagate to the dependent compile and link phases to produce a debug build. Note that option overrides will *not* propagate to other dependency `ProjectPhase`s.
* When an `action` such as `clean` or `build` is called on a phase, that action is first called on each of that phase's dependency phases, and so on down the graph. The actions are then performed on the way back up, in depth-first order. A phase which doesn't implement a particular action simply ignores it. Note that actions *do* propagate to other dependency `ProjectPhase`s; a `build` action builds everything in a dependency graph.

> Note that the confluence of `Phase` class heierarchies and `Phase` dependencies must be carefully considered. Derived phases inherit options polymorphically, and a `Phase` object's most derived phase class that can perform a particular action will be the one to do so; dependency phases *all* inherit option overrides from their dependent *project phases*, and *all* perform any action called to their dependents, if *any* phase in their class hierarchies can do so.

## Actions

Pyke is not just good for building. There are other standard actions it can perform, with more forthcoming. Actually, it's more correct to say that `Phase` objects perform actions. Any string passed as an action on the command line will be called on the starter phase (after its dependencies, etc). If no phase supports the action, it is quietly ignored.

### Built-in actions

Currently, the supported actions in each built-in phase are:

|phase class|actions
|---|---
|Phase|report_options
|CFamilyBuildPhase|(none; all actions are defined by subclasses)
|CompilePhase|clean; clean_build_directory; build
|LinkPhase|clean; clean_build_directory; build
|CompileAndLinkPhase|clean; clean_build_directory; build
|ProjectPhase|(none; all actions are the responsiblity of dependencies)

These can be spcified on the command line. Multiple actions can be taken in succession; see below for CLI operation.

### Action aliases

There are built-in aliases for the defined actions, to save some effort:

|alias|actions
|---|---
|report-options|report_options
|opts|report_options
|c|clean
|clean-build-directory|clean_build_directory
|cbd|clean_build_directory
|b|build

You can define others in a config file. Pyke looks for configs in the following order:
* ~/.config/pyke/pyke-config.json
* <project-root>/pyke-config.json
* $CWD/pyke-config.json

## Options

Options do not have to be strings. They can be any Python type, really, with the following criteria:

- Options should be *convertible* to strings.
- Options must be copyable (via `copy.deepcopy()`).

We've already seen list-type options, and there are several of those in the built-in phase classes. Custom ANSI colors for output are stored as dictionaries of dictionaries. And of course, any phase class you create can use any new option types you desire, as long as they meet the above criteria.

### Overrides are stacked

When an option is applied to a phase which already has as option by the same name, it is called an `override`. The new option displaces or modifies the existing one, but it does not replace it internally. Rather, it is pushed onto the option's *stack* of values, and can later be *popped* to undo the modification. In this way, an override can, say, remove an entry from an option's listed elements, and later popping of that override will bring it back.

### Override operators

So how does one specify that an override *modifies* an option, instead of *replacing* it? When specifying the name of the option to set, you can provide '+' or '-' or another operator to specify the modifier. A few option types get special behavior for this syntax:

|original type|operator|override type|effect
|---|---|---|---
|any|=, none|any|the option is replaced by the override
|int\|float|+=, -=, *=, /=|int\|float|performs standard math operations
|string|+=  |any|appends str(override) to the end of the string
|string|-=  |string|removes the first instance of the override string from the string
|list|+=  |any|the override is appended to the list
|list|*=  |list\|tuple|the override elements extend the list
|list|-=  |any|the override is removed from the list
|list|\\=  |int|the override specifies an index to remove from the list
|list|\\=  |list[int]\|tuple[int]\|set[int]|the override specifies a collection of indices to remove from the list
|tuple|+=  |any|the override is appended to the tuple
|tuple|*=  |list\|tuple|the override elements extend the tuple
|tuple|-=  |any|the override is removed from the tuple
|tuple|\\=  |int|the override specifies an index to remove from the tuple
|tuple|\\=  |list[int]\|tuple[int]\|set[int]|the override specifies a collection of indices to remove from the list
|set|+=, \|=|any non-set|the override is added to the set
|set|-=  |any|the override is removed from the set
|set|\|=  |set|the result is unioned with the set 
|set|&=  |set|the result is intersected with the set
|set|\\=  |set|the result is the difference with the set
|set|^=  |set|the result is the symmetric difference with the set
|dict|+=  |dict|the result is the union with the dict
|dict|-=  |any|the entry is removed from the dict by key
|dict|\|=  |dict|the result is the union with the dict

<!--TODO: some examples here-->

### Viewing options

The base `Phase` class defines the `report-options` action, with an alias of `opts`. This action prints the phases in depth-first dependency order, and each phase's full set of options in both raw, uninterpolated form, and fully interpolated form. This makes it easy to see what options are available, the type each is set to by default, and how interpolation and override operations are affecting the final result. It's handy for debugging a difficult build.

```
$ pyke opts
phase: simple_app
name: = unnamed
      = simple
     -> simple
verbosity: = 0
          -> 0
project_anchor: = /home/schrock/src/pyke/tests/simple_app
               -> /home/schrock/src/pyke/tests/simple_app
gen_anchor: = /home/schrock/src/pyke/tests/simple_app
           -> /home/schrock/src/pyke/tests/simple_app
simulate: = False
         -> False
...
```

Each option is listed with all its stacked raw values, followed by the interpolated value. Notice above that the default name, `unnamed`, is overridden (by a replacement operation) with `simple`, as defined in the makefile. You can also easily see how command-line overrides are affecting the results. More on how to set them below, but overriding the `verbosity` option with `2` looks like this:

```
$ pyke -o name:less_simple report
phase: less_simple
name: = unnamed
      = simple
     -> simple
verbosity: = 0
           = 2
          -> 2
project_anchor: = /home/schrock/src/pyke/tests/simple_app
               -> /home/schrock/src/pyke/tests/simple_app
gen_anchor: = /home/schrock/src/pyke/tests/simple_app
           -> /home/schrock/src/pyke/tests/simple_app
...
```

Here again, `verbosity` has been overridden, and has a second value on its stack. Subsequent actions will report more or less information based on the verbosity.

The detailed report from `report_options` (`opts`) is what you get at `report_verbosity` level `2`. If you want to see only the interpolated values, you can override the `report_verbosity` option to `1`:

```
$ pyke -o report_verbosity:1
phase: simple_app
name: -> simple
verbosity: -> 2
project_anchor: -> /home/schrock/src/pyke/tests/simple_app
gen_anchor: -> /home/schrock/src/pyke/tests/simple_app
...
```

### Interpolation

The details on interpolation are straighforward. They mostly just work how you might expect. A portion of a string value surrounded by `{}` may contain a name, and that name is then used to get the option by that name. The option is converted to a string, if it isn't already (it probably is), and replaces the substring and braces inline, as previously explained. This means that interpolating an option which is a list will expand that list into the string:
```
$ pyke -o "list_of_srcs:Sources: {sources}" report
...
list_of_srcs: = Sources: {sources}
              = Sources: ['a.cpp', 'b.cpp', 'c.cpp', 'main.cpp']
...
```

If the entire value of an option is interpolated, rather than a substring, then the value is replaced entirely by the referenced option, and retains the replacement's type. This is useful for selecting a data structure by name, as explained below.

#### Nested interpolated string

One useful feature is that interpolations can be nested. `CFamilyBuildPhase` uses this in places to help resolve selectable options. Look carefully at `kind_optimization`'s raw value below. It contains four `{}` sets, two inside the outer, and one nested even deeper. The inner set is interpolated first, and then the outer set according to the new value.

```
$ pyke report
...
kind: = release
     -> release
...
tool_args_gnu: = gnuclang
              -> gnuclang
tool_args_clang: = gnuclang
                -> gnuclang
...
gnuclang_debug_optimization: = 0
                            -> 0
...
gnuclang_release_optimization: = 2
                              -> 2
...
kind_optimization: = {{tool_args_{toolkit}}_{kind}_optimization}
                  -> 2
...
```

So `kind_optimization` evolves as:

```
kind_optimization: -> {{tool_args_{toolkit}}_{kind}_optimization}
                   -> {{tool_args_gnu}_{kind}_optimization}
                   -> {gnuclang_{kind}_optimization}
                   -> {gnuclang_release_optimization}
                   -> 2
```

Now, when overriding `kind`, a different version of the optimization flags (passed as -On to gcc, say) will be automatically interpolated:

```
$ pyke -o kind:debug report
...
kind: = release
      = debug
     -> debug
...
kind_optimization: = {{tool_args_{toolkit}}_{kind}_optimization}
                  -> 0
...
```

### Overriding in the makefile

When constructing phase objects, the options you declare are technically overrides, if they happen to have the same name as options in any base class. They are treated by default as replacements, though you can provide operators.

You can also explicitly override after phase creation:

```python
import pyke as p

phase = p.CompileAndLinkPhase({
    'name': 'simple_experiemtal',
    'sources': ['a.cpp', 'b.cpp', 'c.cpp', 'main.cpp'],
    'exe_basename': '{name}',
    'include_dirs': (OptionOp.APPEND, 'include/exp')      # appending to include_dirs
})

p.push_opts({                 # appending to sources
    'sources': (OptionOp.APPEND, [f'exp/{src}' for src in ['try_this.cpp', 'maybe.cpp', 'what_if.cpp']])
})

p.main_project().set_dependencies(phase)
```

You can pop the override with `Phase.pop_opts(key)`. (Without the arguemts or operators.) This is obviously a contrived example, but it showcases the `push_opts` method.

> `Phase.push_opts` is defined on `Phase` as:
> ``` def push_opts(self, overrides: dict, include_deps: bool = False, include_project_deps: bool = False) ```
> The boolean parameters tell pyke how to propagate overrides through dependency phases. `include_deps` includes dependencies which are not `ProjectPhase`s, and `include_project_deps` includes only `ProjectPhase` phases specifically. Options set in `Phase` constructors call `push_opts` with both set to `False`. `ProjecPhase` overrides `push_opts` to make `include_deps` to be `True` by default. These defaults allow overrides set from the command line propagate appropriately. If set upon a project phase (the default phase), all the project's non-project dependencies will get the override, whereas if set on a non-project phase with `-p`, only that phase will get the override.

### Overriding on the command line

As seen previously, overrides can be specified on the command line as well with `-o <option<op>value>`. This can look similar to overrides in code (though you may need to enquote it):

```
$ pyke -o colors:colors_none build
$ pyke -o "sources += [exp/try_this.c, exp/maybe.c, exp/what_if.c]" report
```
String values can be in quotes if they need to be disambiguated from punctuation. The usual escapements work with '\'. Overrides you specify with `[]` are treated as lists, `()` as tuples, `{}` as sets, and `{:}` as dicts. Since option keys must only contain letters, numbers, and underscores, you can differentiate a single-valued set from an interpolation by inserting a comma, or specifically enquoting the string:

```
$ pyke -o "my_set_of_one:{foo,}" ...
$ pyke -o "my_set_of_one:{'foo'}" ...
```

There is more to say about how value overrides are parsed. Smartly using quotes, commas, or spaces to differentiate strings from interpolators will usually get you where you want. Generally, though, setting options in the makefile will probably be preferred.

### Base pyke options

There are a few options that are uiversal to pyke, regardless of the type of project it is running. Here are the options you can set to adjust its behavior:

|option|default|usage
|---|---|---
|name|phase|The name of the phase. You should likely override this.
|report_verbosity|2|The verbosity of reporting. 0 just reports the phase by name; 1 reports the phase's interpolated options; 2 reports the raw and interpolated options.
|verbosity|0|The verbosity of non-reporting actions. 0 is silent, unless there are errors; 1 is an abbreviated report; 2 is a full report with all commands run.
|project_anchor|\<project root\>|This is an anchor directory for other directories to relate to when referencing required project inputs like source files.
|gen_anchor|\<project root\>|This is an anchor directory for other directories to relate to when referencing generated build artifacts like object files or executables.
|colors|{colors_24bit}|Specifies the name of a color palette to use in reports and other output. Colors are discussed below; you can set this value to `{colors_none}` to disable color output.

When running pyke from a directory that is different from your makefile's directory, you can specify the makefile path with `-m`. This is discussed below, but by default both the project root directory (`project_anchor`) and generated output root directory (`gen_anchor`) are relative to the makefile's directory, regardless of where you invoke from. However, this behavior can be modified. By overriding `gen_anchor` to a different directory in your file system, you can cause all the generated outputs to be placed anywhere. The generated directory structure remains the same, just at a different root location. Note that intermediate files which are inputs of later phases, like compiled object files, are still resolved correctly, as *any* generated file is rooted by `gen_anchor`. Likewise, any file that is expected as part of the project inputs created by developers (anything you might check in to your project repository, say) is anchored by `project_anchor`.

If you don't want your makefile to be situated at the project root, overriding `project_anchor` (possibly in the makefile itself) to the actual project root will line things up.

### C/C++ specific options

Pyke began as a build tool for C and C++ style projects. The requisite classes are those that derive from `CFamilyBuildPhase`, and have lots of options for controlling the build. Note that since clang and gcc share much of the same command arguments, their toolchain-specific arguemts are often combined into a single definition.

|option|default|usage
|---|---|---
|toolkit|gnu|Sets which system build tools to use. `gnu` uses gcc; `clang` uses clang; `visualstudio` uses Visual Studio's compiler.
|language|C++|Sets the language.
|language_version|23|Sets the language version.
|kind|release|Release or debug build. See below for adding new kinds.
|taregt_os_gnu|posix|Specifies UNIX or GNU/Linux as the target OS for the build. Determined by the toolkit.
|target_os_clang|posix|Specifies UNIX or GNU/Linux as the target OS for the build. Determined by the toolkit.
|target_os_visualstudio|windows|Specifies MS Windows as the target OS for the build. Determined by the toolkit.
|tool_args_gnu|gnuclang|Specifies either gcc or clang as the primary build tool. Determined by the toolkit.
|tool_args_clang|gnuclang|Specifies either gcc or clang as the primary build tool. Determined by the toolkit.
|tool_args_visualstudio|visualstudio|Specifies Visual Studio as the primary build tool. Determined by the toolkit.
|gnuclang_warnings|['all', 'extra', 'error']|Sets warning flags. These are toolkit-specific.
|gnuclang_debug_debug_level|2|Debug level during debug builds. Sets n as passed by -g\<n\> to gnu/clang.
|gnuclang_debug_optimization|g|Optimization level during debug builds. Sets n as passed by -O\<n\> to gnu/clang.
|gnuclang_debug_flags|[-fno-inline, -fno-lto, -DDEBUG]|Additional flags passed to gnu/clang during debug builds.
|gnuclang_release_debug_level|0|Debug level during release builds. Sets n as passed by -g\<n\> to gnu/clang.
|gnuclang_release_optimization|2|Optimization level during release builds. Sets n as passed by -O\<n\> to gnu/clang.
|gnuclang_release_flags|[-DNDEBUG]|Additional flags passed to gnu/clang during release builds.
|visualstudio_warnings|[]|Sets warning flags. These are toolkit-specific.
|visualstudio_debug_debug_level||Debug level during debug builds. Sets n as passed by [?] to Visual Studio.
|visualstudio_debug_optimization||Optimization level during debug builds. Sets n as passed by [?] to Visual Studio.
|visualstudio_debug_flags|[]|Additional flags passed to Visual Studio during debug builds.
|visualstudio_release_debug_level||Debug level during release builds. Sets n as passed by [?] to Visual Studio.
|visualstudio_release_optimization||Optimization level during release builds. Sets n as passed by [?] to Visual Studio.
|visualstudio_release_flags|[]|Additional flags passed to Visual Studio during relase builds.
|debug_level|{{tool_args_{toolkit}}_{kind}_debug_level}|Maps the tool-specific debug level.
|optimization|{{tool_args_{toolkit}}_{kind}_optimization}|Maps the tool-specific optimization flags.
|kind_flags|{{tool_args_{toolkit}}_{kind}_flags}|Maps any tool-specific debug or release flags.
|warnings|{{tool_args_{toolkit}}_{kind}_warnings}|Maps any tool-specific wargning flags.
|pkg_config|[]|Specifies a list of packages which are passed into `pkg-config` for automatically specifying include directories and libraries.
|posix_threads|False|Specifies a posix multithreaded program.
|definitions|[]|Specifies a set of macro definitions.
|additional_flags|[]|Specifies a set of additional flags passed to the compiler.
|incremental_build|True|If set, and using the `CompileAndLink` phase, forces the build to create individual object for each source, and link them in a separate step. Otherwise, the build will pass all the sources to the build tool at once, to create a binary target in one step.
|include_anchor|{project_anchor}|The base directory for include search directories.
|include_dirs|[include]|The default directories where project headers are searched.
|src_dir|src|The default directory where source files can be found.
|src_anchor|{project_anchor}/{src_dir}|The full directory layout where source files can be found.
|sources|[]|A list of source files to compile in this phase.
|build_dir|build|The default subdirectory to place all build results into.
|build_detail|{kind}.{toolkit}|A default subdirectoy of {build} where more specific build results are placed.
|build_anchor|{gen_anchor}/{build_dir}|
|build_detail_anchor|{build_anchor}/{build_detail}|
|obj_dir|int|A default subdirectory where intermediate files are placed.
|obj_basename||The base file name of the generated object file. An empty string means to use the basename of the first source in {sources}.
|posix_obj_file|{obj_basename}.o|Constructs the object file name for UNIX or GNU/Linux environments.
|windows_obj_file|{obj_basename.obj|Constructs the object file name for MS Windows environments.
|obj_file|{{target_os_{toolkit}}_obj_file}|How to name the generated object file.
|obj_anchor|{build_detail_anchor}/{obj_dir}|The full directory layout of intermediate files.
|obj_path|{obj_anchor}/{obj_file}|The final full path of the generated object file.
|exe_dir|bin|A default subdirectory where final executable files are plced.
|exe_basename|{name}|The file name of the generated executable file.
|posix_exe_file|{exe_basename}|Constructs the executable file name for UNIX or GNU/Linux environments.
|windows_exe_file|{exe_basename}.exe|Constructs the executable file name for MS Windows environments.
|exe_file|{{target_os_{toolkit}}_exe_file|Maps the executable file name.
|exe_anchor|{build_detail_anchor}/{exe_dir}|The full directory layout of executable files.
|exe_path|{exe_anchor}/{exe_file}|The full path of the executable file to build.
|lib_dirs|[]|A list of library directories.
|libs|[]|A list of libraries to link with.
|shared_libs|[]|A list of shared objects to link with.
|exe_path|{exe_anchor}/{exe_basename}|The final full path of the generated executable file.

### Making sense of the directory optinos

Each of the include, source, object, and executable directories are built from components, some of which you can change to easily modify the path. Pyke is opinionated on its directory structure, but you can set it how you like.

#### Include files
```
inc_dir = .
include_anchor = {project_anchor}/{inc_dir}/\<include directory\>
include_dirs = [include]
```
You are encouraged to change `inc_dir` to set a base directory for all include directories. Pyke will reference `include_anchor` and `include_dirs` directly; the rest are just there to construct the path.

#### Source files
```
src_dir = src
src_anchor = {project_anchor}/{src_dir}/\<source file\>
```
You are encouraged to change `src_dir` to set a base directory for all the source files.

#### Build base directory structure
```
build_dir = build
build_detail = {kind}.{toolkit}
build_anchor = {gen_anchor}/{build_dir}
build_detail_anchor = {build_anchor}/{build_detail}
```
You are encouraged to change `build` to set a different base for generated files. Pyke will reference `src_anchor` and `sources` directly.

#### Intermediate (object) files
```
obj_dir = int
obj_basename = \<source_basename\> (named after either a source file or the phase name, depending on `intermediate_build` and the phase type)
obj_file = {obj_basename}.o  (.obj on Windows)
obj_anchor = {build_detail_anchor}/{obj_dir}
obj_path = {obj_anchor}/{obj_file}
```
You are encouranged to change `obj_dir` to set a base directory for intermediate files. Pyke will only reference `obj_path` directly, and will override `obj_basename` for each source file.

#### Binary (executable) files
```
exe_dir = bin
exe_basename = {name}
exe_file = {exe_basename}  (with .exe on Windows)
exe_anchor = {build_detail_anchor}/{exe_dir}
exe_path = {exe_anchor}/{exe_file}
```
You are encouraged to change `exe_dir` to set a base directory for executable files, and `exe_basename` to set the name of the executable. Pyke will only reference `exe_path` directly.

Of course, you can change any of these, or make your own constructed paths.

## The CLI

The general form of a pyke command is:

```
pyke [ -v | -h | [-c]? [-m makefile]? ]? [-o key[:value] | -p phase | [action]* ]*
```

Notably, -o, -p and action arguments are processed in command-line order. You can set the phase to use with -p, set some option overrides, perform actions on that phase, set a different phase, set more options, perform more actions, etc. The default created project phase is the default phase.

The command line arguments are:
* `-v`, `--version`: Prints the version information for pyke, and exits.
* `-h`, `--help`: Prints a help document.
* `-c`, `--cache_makefile`: Allows the makefile's __cache__ to be generated. This might speed up complex builds, but they'd hvae to be really complex. Must precede any arguments that are not -v, -h, or -m.
* `-m`, `--module`: Specifies the module (pyke file) to be run. Must precede any arguments that are not -v, -h, or -c. Actions are performed relative to the module's directory, unless an option override (-o anchor:[dir]) is given, in which case they are performed relative to the given working directory. Immediately after running the module, the active phase is selected as the last phase added to use_phase()/use_phases(). This can be overridden by -p. If no -m argument is given, pyke will look for and run ./make.py.
* `-o`, `--override`: Specifies an option override in all phases for subsequenet actions. If the option is given as a key:value pair, the override is set; if it is only a key (with no separator ':') the override is clear. Option overrides are kept as a stack; if you set an override n times, you must clear it n times to restore the original value. 
* `-p`, `--phase`: Specifies the active phase to use for subsequent option overrides and actions. Phases are named like: `\<ProjectPhase name\>.\<Non-ProjectPhase name\>. See just below.
* `action`: Arguments given without switches specify actions to be taken on the active phase's dependencies, and then the active phase itself, in depth-first order. Any action on any phase which doesn't support it is quietly ignored.

The main project phase is named according to 1) the name of the makefile, unless it is specifically named `make.py`, in which it is named 2) the name of the directory in which it resides. So, if your project's root contins the makefile, and is named like this:
``` ~/src/asset_converter/make.py ```
The project will be called "asset_converter". If, however, it is named like:
``` ~/src/asset_converter/images_make.py ```
The project will be called "images_make". (Maybe you have several pyke makefiles at the root.)

Dependency phases of any project phase which are not themselves project phases are specified by the dotted name. Maybe your `asset_converter` project has dependencies like this:
```
asset_converter (ProjectPhase)
├── image_converter (ProjectPHase)
│   └── link (LinkPhase)
│       ├── compile_jpg (CompilePhase)
│       ├── compile_png (CompilePhase)
│       └── compile_tga (CompilePhase)
└── mesh_converter (ProjectPhase)
    └── link (LinkPhase)
        ├── compile_blender (CompilePhase)
        ├── compile_3ds (CompilePhase)
        └── compile_dxf (CompilePhase)
```
Here, each phase will be named by its owning project phase and its non-project phase names:
* `image_converter.link`
* `image_converter.compile_jpg`
* `image_converter.compile_png`
* `image_converter.compile_tga`
* `mesh_converter.link`
* `mesh_converter.compile_blender`
* `mesh_converter.compile_3ds`
* `mesh_converter.compile_dxf`

Note that the naming is *not* strictly hierarchical, but rather, specifically `project.non-project`. Non-project phases must always be uniquely named within a project, and projects must always be uniquely named among each other. When referring to a phase on the command line with `-p`, this is the naming to use.

## Advanced Topics

### Adding new phases

Of course, a benefit of a programmatic build system is extension. Building your own Phase classes shold be straightforward. You likely won't have to often.

Say you need a code generator. It must make .c files your project must compile and link with extant source. You can write a custom Phase-derived class to do just this. This gets you into the weeds of `Step` and `Result` classes, and action steps. More help will be provided in the future, but for now, let's just look at the code:

```python
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
    ''' Custom phase class for implementing some new, as-yet unconcieved actions. '''
    def __init__(self, options, dependencies = None):
        options = {
            'name': 'generator',
            'gen_src_dir': '{src_anchor}/gen',
        } | options
        super().__init__(options, dependencies)

    def make_generated_source(self):
        ''' Make the path and content of our generated source. '''
        return { Path(f"{self.opt_str('gen_src_dir')}/{src_file}"): src
                 for src_file, src in gen_src.items() }

    def do_action_clean(self, action: Action):
        ''' Cleans all object paths this phase builds. '''
        res = ResultCode.SUCCEEDED
        for src_path, _ in self.make_generated_source().items():
            res = res.failed() or self.do_step_delete_file(src_path, action)
        return res

    def do_action_clean_build_directory(self, action: Action):
        ''' Wipes out the generated source directory. '''
        return self.do_step_delete_directory(Path(self.opt_str('gen_src_dir')), action)

    def do_action_build(self, action: Action):
        ''' Generate the source files for the build. '''
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
```

There's a bit going on, but it's not terrible. This uses some facilities available in `CFamilyBuildPhase` to clean generated source and the generation directory, as well as making directories for the build. The main work is in generating the source files in an appropriate generation directory.

Integrating this custom phase into your makefile is as simple as making a new instance of the new phase, and setting it as a dependency of the build phase:

```python
'Bsic test with custom phase'

from custom import ContrivedCodeGenPhase
import pyke as p

gen_phase = ContrivedCodeGenPhase({})

build_phase = p.CompileAndLinkPhase({
    'name': 'simple',
    'sources': ['a.c', 'b.c', 'c.c', 'gen/d.c', 'gen/e.c', 'main.c'],
    'exe_basename': '{name}',
}, gen_phase)

p.main_project().set_dependency(build_phase)
```

And that's it. Now the `build` action will first generate the files in the right place, and then build them. The `clean` action will delete the generated files, and the `clean_build_directory` action will not only remove the build, but also the generated source directory.

#### Adding new actions

To add a new action to a custom phase, simply add a method to the phase class called `do_action_<action_name>(self, action: Action) -> ResultCode`. (You'll want to import Action and ResultCode from pyke if you want the annotations.) That's all you need to do for the method to be called on an action, since actions' names are just strings, and pyke reflects on method names to find a phase that can handle the action.

### Adding new build kinds

Adding new build kinds is straightforward if you're just trying to customize the system build commands. There are currently three that depend on the build kind: `debug_level`; `optimization`; and `flags`. For POSIX tools, these correspond to the `-g{debug_level}`, `-O{optimization}`, and `{flags}` of any definition. If you wanted a custom kind called "smallest", imply provide the following overrides, with perhaps these values:

            'gnuclang_smallest_debug_level': '0',
            'gnuclang_smallest_optimization': 's',
            'gnuclang_smallest_flags': ['-DNDEBUG'],

When selecting the build kind with `-o kind=smallest`, these overrides should be selected for the build.

<!-- TODO: Actually test this. -->

### Setting colors

The colorful output can be helpful, but not if you're on an incapable terminal, or just don't like them or want them at all. You can select a color palette:

```
```
