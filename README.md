# pyke

Pyke is a python-based, extensible system for building and operating software projects. Its first functions centered around cleaning and building C and C++ projects, but it can do much more. Future development work will expand languages and environments in which pyke can be useful, actions such as running, installing, deploying and testing, and will support a plugin interface for expansion beyond the core.

## The rationale

Pyke is being designed to act initially as an alternative to CMake. I'm not expert in CMake, and many of the below may also apply to it, but I wanted to build pyke as a personal project, and use it in other projects of my own.

- **Minimal artifacts**
Within a project, the only artifacts that result from a build operation are the intermediate files from the build itself (.o files, specifically, for C-family projects) and the final output. The only necessary support file in a project is the make.py file itself, probably at the project root folder.

- **Flexibility**
Of course, the pyke project file doesn't have to be at the root of a project. And it doesn't have to be called make.py. A pyke file can specify specific anchor directories for project files and generated artifacts. Command-line overrides can modify them in times of need.

- **Just-beyond-declarative configuration**
Usually, a declarative syntax is desireable for systems like this. But even CMake is a sort of language, and pyke files are too--just, in python. Very basic python is all you need to know to use it fully, and when you need that convenience of a full language, it's very nice to have. Sane defaults and a simple object structure help keep things somewhat minimal for a basic build.

- **Extensibility**
Pyke comes with some basic classes (called `Phase`s) which can manage basic tasks. But you may have special needs in your project tha require a specific tool to be run, or files to be moved around, or secret keys to be managed, etc. If it's not in the basic set of classes, build your own. It's a reasonable interface to design new functionality for.

Eventually there will be a plugin interface for separate extension projects. This is still being designed, and the basic builtin classes are being fleshed out now.

## Installing pyke

Couldn't be easier. You need to be running python3.10 at least, and have pip installed. To install it globally:

```bash
$ pip install pyke
```
or,
```bash
$ pip install --user pyke
```

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

p.use_phases(phase)
```

Now it's as simple as invoking pyke:

```bash
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

So what's in this `make.py` file? The general execution is to start pyke, and pyke will then find your `make.py` makefile in the current directory (your project root). Pyke will import the makefile, run it, and then begin executing actions based on what your makefile has configured. All `make.py` does, in the simple cases, is add `Phase`-derived objecs to the pyke environment. Pyke does the rest.

So in the example above, first `make.py` imports the important pyke symbols. Then it sets up a single phase: `CompileAndLinkPhase`. In its definiton are three `option`s: One sets the name of the phase (not strictly necessary, but good practice as it can be handy), one specifies the C++ sources, and one sets the name of the resulting executable binary file based on the phase's name (`simple` in this case; more on how `{string}`s are interpolated below). The phase is then registered to pyke via the `use_phases()` function. Pyke will use the phases it's given, along with the command line arguments, to perform the needed tasks: In a linux environment, for example, it will make the appropriate directories, invoke gcc or clang with configured arguments, and optionally report its progress.

### So how does pyke know where to find the sources? Or the headers?

Every `Phase`-derived class defines its own default options, which give a default configuration for its actions. As an example, one option in `CompileAndLinkPhase` is `src_dir`, which specifies the directory relative to the project root where source files can be located. The default is `src`, which also happens to be where `simple`'s source files are stored. Similarly, `simple`'s headers are stored in `include`, and `CompileAndLinkPhase` has another option named `include_dirs` which contains `[include]`. Note that this is a list of length one, holding the default directory where include files are to be found. When it comes time to build with, say, `gcc`, the `include_dirs` value becomes `-Iinclude`, and the source files are given as source arguments to `gcc`. There is more to the story of how directories are determined, but this suffices for the moment.

Every option can have its default value modified or replaced. If your source files are stored in a different directory (say, `source` instead of `src`), you can add `'src_dir': 'source'` to the phase definition, and pyke will find the files.

> You can also set `src_dir` to `'.'`, the dot directory, and explicitly path each source file, like:
> `"'sources': ['src/a.c', 'src/b.c', 'src/c.c', 'src/main.c']"`
> Though, of course, that's just more text.

### Interpolation, basically

In a nutshell, a string value in an option can have all or part of it enclosed in `'{''}'`. This signifies an interpolation, which is simply to replace that portion of the string with the option given by the name in braces. The name is recursively looked up in the options table, its string values interpolated the same way, and returned to replace. Above, the executable name (`'exe_basename'`) is interpolated as `'{name}'`. The text is replaced by `simple`, the value of the `name` option.

> It should be noted that most of these options so far are actually contained in a `Phase`-derived class called `CFamilyBuildPhase`, which `CompileAndLinkPhase` derives from. This is because several other `CFamilyBuildPhase`-derived classes make use of the same options. It works just the same, as derived phase class inherit their supers' options.

## Phases

Phases represent the transformation of files--inputs to outputs. Any useful build phase will have input files and output files. Some of these may be source, authored by developers. Some may be created by compiling source to object, linking objects to executables or libraries, cloning repos, or running code generation tools. When the outputs of one phase are the inputs of another, the one is a `dependency` of the other. Dependencies are set in the makefile explicitly, but their output->input mechanistry is automatic once set.

A specific phase may be invoked on the command line with `-p <phase-name>`, referencing the `name` of the phase, but this is optional. If a phase is not specified, then the *last* phase passed to `pyke.use_phases()` in the makefile is the default phase.

Each operation of a build may have a dedicated phase. C/C++ builds that are more complex than `simple` above are likely to have a `CompilePhase` instance dedicated to each single source file->object file transformation. Phases can be cloned, and their options as set at the time of cloning are copied with them. So, a template `CompilePhase` can be preset, and each clone made have its requisite source file set to `src`. Each `CompilePhase` object would then be set as a dependency of a `LinkPhase` object, which will automatically gather the generated object files from each `CompilePhase` for linking. Such an example makefile might look like this (with an additional few source files in a differnt directory, for spice):

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

p.use_phases(o_to_exe_phase)
```

### Built-in phases

Pyke comes with some built-in `Phase` classes--not many yet, but it's early still:
* `class Phase`: Common base class for all other phases
* `class CFamilyBuildPhase(Phase)`: Common base class for building C and C++ projects.
* `class CompilePhase(CFamilyBuildPhase)`: Phase for compiling a single source file to a single object file.
* `class LinkPhase(CFamilyBuildPhase)`: Phase for linking objects together to form a final archive, shared object, or executable binary.
* `class CompileAndLinkPhase(CFamilyBuildPhase)`: Phase for combining compile and link operations into one phase, perhaps with a single call to the native build tool.

An easier view of the class heierarchy:
```
Phase
├── CFamilyBuildPhase
│   ├── CompilePhase
│   ├── LinkPHase
│   └── CompileAndLinkPhase
```

### Dependencies

As mentioned, dependencies among phases are set in the makefile. There are several things to know about dependency relationships:
* They cannot be cyclical. The dependency graph must not contain loops, though diamond relationships are fine. (Common dependent phase instances will only perform a particular action once.)
* When options are set to a phase, they override already-set options in that phase, *and all the dependent phases as well*. This enables one to set an option such as `'kind': 'debug'` in, say, a link phase, and have that propagate to the dependent compile phases to produce a debug build.
* When an `action` such as `clean` or `build` is called on a phase, that action is first called on each of that phase's dependency phases, and so on up the graph. The actions are then performed on the way back, in depth-first order. A phase which doesn't implement a particular action simply ignores it.

> Note that the confluence of `Phase` class heierarchies and `Phase` dependencies must be carefully considered. Derived phases inherit options polymorphically, and the most derived phase that can perform a particular action will the the one to do so; dependent phases *all* inherit option overrides from their dependents, and *all* perform any action called to their dependents, if *any* phase in their class heierarchy can do so.

## Actions

Pyke is not just good for building. There are other standard actions it can perform, with more forthcoming. Actually, it's more correct to say that `Phase` objects perform actions. Any string passed as an action on the command line will be called on the starter phase (after its dependencies, etc). If no phase supports the action, it is quietly ignored.

### Built-in actions

Currently, the supported actions in each built-in phase are:

|phase class|actions
|---|---
|Phase|report
|CFamilyBuildPhase|clean; build
|CompilePhase|clean; build
|LinkPhase|clean; build
|CompileAndCFamilyBuildPhase|clean; build

These can be spcified on the command line. Multiple actions can be taken in succession; see below for CLI operation.

## Options

Options do not have to be strings. They can be any Python type, really, with the following criteria:

- Options should be *convertible* to strings.
- Options must be copyable (via `copy.deepcopy()`).

We've already seen list-type options, and there are several of those. Custom ANSI colors for output are stored as dictionaries. And of course, any phase class you create can use any new option types you desire, as long as they meet the above criteria.

### Overrides are stacked

When an option is applied to a phase which already has as option by the same name, it is called an `override`. The new option displaces or modifies the existing one, but it does not replace it internally. Rather, it is pushed onto the option's *stack* of values, and can later be *popped* to undo the modification. In this way, an override can, say, remove an entry from an option's listed elements, and later popping that override will bring it back.

### Override operators

So how does one specify that an override *modifies* an option, instead of *replacing* it? When specifying the name of the option to set, you can append the name with '+' or '-' to specify adding / extending or removing. Only a few option types get special behavior for this syntax:

|original type|operator|override type|effect
|---|---|---|---
|any|=, none|any|the option is replaced by the override
|list|+  |any|the override is appended to the list
|list|*  |list\|tuple|the override elements extend the list
|list|-  |int|the override specifies an index to remove from the list
|list|-  |list[int]\|tuple[int]|the override specifies a collection of indices to remove from the list
|tuple|+  |any|the override is appended to the list
|tuple|*  |list\|tuple|the override elements extend the list
|tuple|-  |int|the override specifies an index to remove from the list
|tuple|-  |list[int]\|tuple[int]|the override specifies a collection of indices to remove from the list
|set|+, \||any|the override is added to the set
|set|-  |any|the override is removed from the set
|set|\|  |set|the result is unioned with the set 
|set|&  |set|the result is intersected with the set
|set|~  |set|the result is the difference with the set
|set|^  |set|the result is the symmetric difference with the set
|dict|+  |dict|the result is the union with the dict
|dict|-  |any|the entry is removed from the dict by key
|dict|\|  |dict|the result is the union with the dict

<!--TODO: some examples here-->

### Viewing options

The base `Phase` class defines the `report` action. This action prints the phases in depth-first dependency order, and each phase's full set of options in both raw, uninterpolated form, and fully interpolated form. This makes it easy to see what options are available, the type each is set to by default, and how interpolation and override operations are affecting the final result. It's handy for debugging a difficult build.

```
$ pyke report
phase: simple
name: = compile_and_link
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

Each option is listed with all its stacked raw values, followed by the interpolated value. Notice above that the default name, "compile_and_link", is overridden by a replacement operation (`=`) with "simple". You can also easily see how command-line overrides are affecting the results. More on how to set them below, but it looks like this:

```
$ pyke -o name:less_simple report
phase: less_simple
name: = compile_and_link
      = simple
      = less_simple
     -> less_simple
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

Here again, `name` has been overridden a second, this time by the command line.

The detailed report is what you get at `report_verbosity` level `2`. If you want to see only the interpolated values, you can override the `report_verbosity` option to `1`:

```
$ pyke -o report_verbosity:1
phase: simple
name: -> less_simple
verbosity: -> 0
project_anchor: -> /home/schrock/src/pyke/tests/simple_app
gen_anchor: -> /home/schrock/src/pyke/tests/simple_app
simulate: -> False
...
```

### Interpolation

The details on interpolation are straighforward. They mostly just work how you might expect. A portion of a string value surrounded by `'{''}'` may contain a name, and that name is then used to get the option by that name. The option is converted to a string, if it isn't already (it probably is), and replaces the substring and braces inline, as previously explained. This means that interpolating an option which is a list will expand that list into the string:
```
$ pyke -o "list_of_srcs:Sources: {sources}" report
...
list_of_srcs: = Sources: {sources}
              = Sources: ['a.cpp', 'b.cpp', 'c.cpp', 'main.cpp']
...
```

If the entire value of an option is interpolated, rather than a substring, then the value is replaced entirely by the referenced option, and retains the replacement's type. This is useful for selecting a data structure by name, as explained below.

#### Nested interpolated string

One useful feature is that interpolations can be nested. `CFamilyBuildPhase` uses this in places to help resolve selectable options. Look carefully at `kind_optimization`'s raw value below. It contains four '{''}' sets, two inside the outer, and one nested even deeper. The inner set is interpolated first, and then the outer set according to the new value.

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
    'include_dirs+': 'include/exp'      # appending to include_dirs
})

p.push_option_override(                 # appending to sources
    'sources+', 
    (f'exp/{src}' for src in ['try_this.cpp', 'maybe.cpp', 'what_if.cpp']))

p.use_phases(phase)
```

(This is obviously a contrived example, but the showcases the `push_option_override` call.)

### Overriding on the command line

As seen previously, overrides can be specified on the command line as well with `-o <option<op>:value>`. This can look similar to overrides in code (though you may need to enquote it):

```bash
$ pyke -o colors:colors_none build
```
<!--
```
$ pyke -o "sources+:[exp/try_this.c, exp/maybe.c, exp/what_if.c]" report
```
-->
<!--
String values can be in quotes if they need to be disambiguated from punctuation. The usual escapements work with '\'. Overrides you specify with '[',']' are treated as lists, '(',')' as tuples, '{','}' as sets, and '{'':''}' as dicts. Since option keys must only contain letters, numbers, and underscores, you can differentiate a single-valued set from an interpolation by inserting a comma:

```bash
$ pyke -o "my_set_of_one:{foo,}" ...
``` -->

As discussed, each override is a push onto an override stack. Option overrides can be popped by omitting the ':<value>' from the -o argument. This might be relevant if performing multple actions, but only want an option set for some:

```bash
$ pyke -o verbosity:2 clean -o verbosity build
```

### Base pyke options

There are a few options that are universal to pyke, regardless of the type of project it is running. Here are the options you can set to adjust its behavior.

|option|default|usage
|---|---|---
|name|phase|The name of the phase. You should likely override this.
|report_verbosity|2|The verbosity of reporting. 0 just reports the phase by name; 1 reports the phase's interpolated options; 2 reports the raw and interpolated options.
|verbosity|0|The verbosity of non-reporting actions. 0 is silent, unless there are errors; 1 is an abbreviated report; 2 is a full report with all commands run.
|project_anchor|<project root>|This is an anchor directory for other directories to relate to when referencing required project inputs like source files.
|gen_anchor|<project root>|This is an anchor directory for other directories to relate to when referencing generated build artifacts like object files or executables.
|simulate|False|This specifies that the build should simulate a run, and not generate real files. This is a near-future feature not yet working.
|colors|{colors_24bit}|Specifies the name of a color palette to use in reports and other output. Colors are discussed below; you can set this value to '{colors_none}' to disable color output.

### C/C++ specific options

Pyke began as a build tool for C and C++ style projects. The requisite classes are those that derive from `CFamilyBuildPhase`, and have lots of options for controlling the build. Note that since clang and gcc share much of the same command arguments, their toolchain-specific arguemts are often combined into a single definition.

|option|default|usage
|---|---|---
|toolkit|gnu|Sets the system build tools to use. `gnu` uses gcc, `clang` uses Clang, `visualstudio` uses Visual Studio's compiler.
|language|C++|Sets the language.
|language_version|23|Sets the language version.
|gnuclang_warnings|['all', 'extra', 'error']|Sets warning flags. These are toolkit-specific.
|kind|release|Release or debug build. See below for adding new kinds.
|gnuclang_debug_debug_level|2|Debug level during debug builds. Sets n as passed by -g<n> to gnu/clang.
|gnuclang_debug_optimization|g|Optimization level during debug builds. Sets n as passed by -O<n> to gnu/clang.
|gnuclang_debug_flags|[-fno-inline, -fno-lto, -DDEBUG]|Additional flags passed to gnu/clang during debug builds.
|gnuclang_release_debug_level|0|Debug level during release builds. Sets n as passed by -g<n> to gnu/clang.
|gnuclang_release_optimization|2|Optimization level during release builds. Sets n as passed by -O<n> to gnu/clang.
|gnuclang_release_flags|[-DNDEBUG]|Additional flags passed to gnu/clang during release builds.
|visualstudio_debug_debug_level|Debug level during debug builds. Sets n as passed by [?] to Visual Studio.
|visualstudio_debug_optimization|Optimization level during debug builds. Sets n as passed by [?] to Visual Studio.
|visualstudio_debug_flags|[]|Additional flags passed to Visual Studio during debug builds.
|visualstudio_release_debug_level|Debug level during release builds. Sets n as passed by [?] to Visual Studio.
|visualstudio_release_optimization|Optimization level during release builds. Sets n as passed by [?] to Visual Studio.
|visualstudio_release_flags|[]|Additional flags passed to Visual Studio during relase builds.
|packages|[]|Specifies a list of packages which are passed into `pkg-config` for automatically specifying include directories and libraries.
|multithreaded|true|Specifies a multithreaded program.
|definitions|[]|Specifies a set of macro definitions.
|additional_flags|[]|Specifies a set of additional flags passed to the compiler.
|incremental_build|true|If set, and using the `CompileAndLink` phase, forces the build to create individual object for each source, and link them in a separate step. Otherwise, the build will pass all the sources to the build tool at once, to create a binary target in one step.

|build_dir|build|The default subdirectory to place all build results into.
|build_detail|{kind}.{toolkit}|A default subdirectoy of {build} where more specific build results are placed.
|obj_dir|int|A default subdirectory where intermediate files are placed.
|exe_dir|bin|A default subdirectory where final executable files are plced.
|obj_anchor|{gen_anchor}/{build_dir}/{build_detail}/{obj_dir}|The full directory layout of intermediate files.
|exe_anchor|{gen_anchor}/{build_dir}/{build_detail}/{exe_dir}|The full directory layout of executable files.

|src_dir|src|The default directory where source files can be found.
|src_anchor|{project_anchor}/{src_dir}|The full directory layout where source files can be found.
|include_dirs|[include]|The default directories where project headers are searched.
|obj_basename||The base file name of the generated object file. An empty string means to use the basename of the first source in {sources}.
|obj_name|{obj_basename}.o|How to name the generated object file.
|obj_path|{obj_anchor}/{obj_name}|The final full path of the generated object file.
|sources|[]|A list of source files to compile in this phase.

|lib_dirs|[]|A list of library directories.
|libs|[]|A list of libraries to link with.
|shared_libs|[]|A list of shared objects to link with.
|exe_basename|{name}|The file name of the generated executable file.
|exe_path|{exe_anchor}/{exe_basename}|The final full path of the generated executable file.

## The CLI

The general form of a pyke command is:

```
pyke [ -v | -h | [-c]? [-m makefile]? ]? [-o key[:value] | -p phase | [action]* ]*
```

Notably, -o, -p and action arguments are processed in command-line order. You can set the phase to use with -p, set some option overrides, perform actions on that phase, set a different phase, set more options, perform more actions, etc. (The last phase to be set to `use_phases` is the default phase.) For a complicated build this might be handy.

The command line arguments are:
`-v`, `--version`: Prints the version information for pyke, and exits.
`-h`, `--help`: Prints a help document.
`-c`, `--cache_makefile`: Allows the makefile's __cache__ to be generated. This might speed up
    complex builds, but they'd hvae to be really complex. Must precede any arguments that 
    are not -v, -h, or -m.
`-m`, `--module`: Specifies the module (pyke file) to be run. Must precede any arguments that
    are not -v, -h, or -c. Actions are performed relative to the module's directory, unless an
    option override (-o anchor:[dir]) is given, in which case they are performed relative to
    the given working directory. Immediately after running the module, the active phase
    is selected as the last phase added to use_phase()/use_phases(). This can be overridden
    by -p.
    If no -m argument is given, pyke will look for and run ./make.py.
`-o`, `--override`: Specifies an option override in all phases for subsequenet actions. If the
    option is given as a key:value pair, the override is set; if it is only a key (with no
    separator ':') the override is clear. Option overrides are kept as a stack; if you set
    an override n times, you must clear it n times to restore the original value. 
`-p`, `--phase`: Specifies the active phase to use for subsequent option overrides and actions.
`action`: Arguments given without switches specify actions to be taken on the active phase's
    dependencies, and then the active phase itself, in depth-first order. Any action on any
    phase which doesn't support it is quietly ignored.

## Advanced Topics

### Simulating the run

### Adding new phases

#### Adding new actions

### Setting colors

### Anchors



