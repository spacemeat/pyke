# pyke

Pyke is a python-based, extensible system for building and operating software projects. Its first functions centered around cleaning and building C and C++ projects, but it can do much more. Future development work will expand languages and environments in which pyke can be useful, actions such as installing, deploying and testing, and may support a plugin interface for expansion beyond the core.

## The rationale

Pyke is being designed to act initially as an alternative to CMake. I'm no expert in CMake, and many of the below may also apply to it, but I wanted to build pyke as a personal project, and use it in other projects of my own.

- **Minimal artifacts**
Within a project, the only artifacts that result from a build operation are the intermediate files from the build itself (.o files, specifically, for C-family projects) and the final output. The only necessary support file in a project is the make.py file itself, probably at the project root folder.

- **Flexibility**
Of course, the pyke project file doesn't have to be at the root of a project. And it doesn't have to be called make.py. A pyke file can specify specific anchor directories for project files and generated artifacts. Command-line overrides can modify them in times of need.

- **Just-beyond-declarative configuration**
Usually, a declarative syntax is desireable for systems like this. But even CMake is a sort of language, and pyke files are too--just, in python. Very basic python is all you need to know to use it fully, and when you need that convenience of a full language, it's very nice to have. Sane defaults and a simple object structure help keep things fairly minimal for a basic project.

- **Extensibility**
Pyke comes with some basic classes (called `Phase`s) which can manage basic tasks. But you may have special needs in your project tha require a specific tool to be run, or files to be moved around, or secret keys to be managed, etc. If it's not in the basic set of classes, build your own. It's a reasonable interface to design new functionality for.

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
from pyke import CompileAndLinkToExePhase, get_main_phase

phase = CompileAndLinkToExePhase({
    'name': 'simple',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
})

get_main_phase().depend_on(phase)
```

Now it's as simple as invoking pyke:

```
$ pyke build
```

The project was quietly built in a subdirectory:

```
├── build
│   └── simple_app.gnu.debug
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
    ├── a.c
    ├── b.c
    ├── c.c
    └── main.c
```

where `build/simple_app.gnu.debug/bin/simple` is the final binary executable.

Of course, this is a very minimal example, and much more configuration is possible. 

## The `make.py` file

So what's in this `make.py` file? The general execution is to start pyke, and pyke will then find your `make.py` makefile in the current directory (your project root). Pyke will import the makefile, run it, and then begin executing actions based on what your makefile has configured and what you specify on the command line. All `make.py` does, in the simple cases, is add `Phase`-derived objecs to a provided top-level `ProjectPhase` object. Pyke does the rest.

So in the example above, first `make.py` imports the important pyke symbols. Then it sets up a single phase: `CompileAndLinkToExePhase`. In its definiton are two options: `name` and `sources`: the specific C source files. Then this phase is added as a `dependency` to a provided main `ProjectPhase`. That's all pyke needs to know how to build.

Pyke always begins with the phase object (a `ProjectPhase` instance), for the whole project. It can be accessed through `pyke.get_main_phase()`, which returns the phase. The CompileAndLinkToExePhase is then registered to the project via the `depend_on()` method. Pyke will use the phases it's given and the options set to each phase, along with the command line arguments, to perform the needed tasks: In this example, it will make the appropriate directories, invoke gcc or clang with configured arguments (in a POSIX environment), and optionally report its progress.

### So how does pyke know where to find the sources? Or the headers? Or where to put things?

Every `Phase`-derived class defines its own default options, which give a default configuration for its actions. As an example, one option in `CompileAndLinkToExePhase` is `src_dir`, which specifies the directory relative to the project root (actually an achor directory, but mnore on that later) where source files can be located. The default is "src", which also happens to be where simple's source files are stored. Similarly, simple's headers are stored in "include", and `CompileAndLinkToExePhase` has another option named `include_dirs` which contains "[include]". Note that this is a `list` of length one, holding the default directories where include files are to be found. When it comes time to build with, say, `gcc`, the `include_dirs` value becomes "-Iinclude", and the source files are given as source arguments to `gcc`. There is more to the story of how directories are determined, but this suffices for the moment.

Every option can have its default value modified or replaced. If your source files are stored in a different directory (say, "source" instead of "src"), you can add `'src_dir': 'source'` to the phase definition, and pyke will find the files.

> You can also set `src_dir` to "'.'", the dot directory, and explicitly path each source file, like:
> `"'sources': ['src/a.c', 'src/b.c', 'src/c.c', 'src/main.c']"`
> Though, of course, that's just more typing.

### Interpolation, basically

In a nutshell, a string value in an option can have all or part of it enclosed in `{}`. This specifies an interpolation, which is simply to replace that portion of the string with the option given by the name in braces. The name is recursively looked up in the options table for that phase, its string values interpolated the same way, and returned to replace. We'll get into detail and examples below.

> It should be noted that most of these options so far are actually contained in a `Phase`-derived class called `CFamilyBuildPhase`, which `CompileAndLinkToExePhase` derives from. This is because several other `CFamilyBuildPhase`-derived classes make use of the same options. It works just the same, since derived phase class inherit their supers' options.

## Phases

Most phases generally represent the transformation of files--inputs to outputs. Any useful build phase will have input files and output files. Some of these may be source, authored by developers. Some may be created by compiling source to objects, linking objects to executables or libraries, cloning repositories, or running code generation tools. When the outputs of one phase are the inputs of another, the one is a `dependency` of the other. Dependencies are set in the makefile explicitly, and their output->input mechanistry is automatic once set.

Each operation of a build, such as the compilation of a single source file, may have a dedicated phase. C/C++ builds that are more complex than "simple" above may have a `CompilePhase` instance dedicated to each single source file->object file transformation, and one for each link operation, etc. Phases can be `cloned`, and their options as set at the time of cloning are copied with them. So, a template `CompilePhase` can be preset, and each clone made have its requisite source file set to `src`. Each `CompilePhase` object would then be set as a dependency of a `LinkToExePhase` object, which will automatically gather the generated object files from each `CompilePhase` for linking. Such an example makefile might look like this (with an additional few source files in a differnt directory, for spice):

```python
'multiphase cloned test'

import pyke as p

c_to_o_phases = []

proto = p.CompilePhase()

for src in ('a.c', 'b.c', 'c.c', 'main.c'):
    c_to_o_phases.append(proto.clone({'name': f'compile_{src}', 'sources': [src]}))

proto = p.CompilePhase({
    'src_dir': 'exp',
    'obj_dir': 'int/exp',
})

for src in ('a.c', 'b.c'):
    c_to_o_phases.append(proto.clone({'name': f'compile_exp_{src}', 'sources': [src]}))

o_to_exe_phase = p.LinkToExePhase({
    'name': 'link',
    'exe_basename': 'simple_1',
}, c_to_o_phases)

p.get_main_phase().depend_on(o_to_exe_phase)
```

Here, we're creating a prototype `CompilePhase` object, and storing clones of it, one for each compile operation, in a list. Those phases become dependencies of the `LinkToExePhase` object, which in turn is set to the main project phase.

### Built-in phases

Pyke comes with some built-in `Phase` classes--not many yet, but it's early still:
* `class Phase`: Common base class for all other phases.
* `class CommandPhase(Phase)`: A generic shell command phase. Often serves as a base class for a custom build step.
* `class CFamilyBuildPhase(Phase)`: Common base class for building C and C++ projects. You won't decleare objecs of this type, but rather subclasses of it, as it does not actually implement many `action`s.
* `class CompilePhase(CFamilyBuildPhase)`: Phase for compiling a single source file to a single object file.
* `class ArchivePhase(CFamilyBuildPhase)`: Phase for building static libraries out of object files.
* `class LinkToSharedObjectPhase(CFamilyBuildPhase)`: Phase for linking objects together to form a shared object (dynamic library).
* `class LinkToExePhase(CFamilyBuildPhase)`: Phase for linking objects together to form an executable binary.
* `class CompileAndArchive(CFamilyBuildPhase)`: Phase for combining compile and archive operations into one phase.
* `class CompileAndLinkToSharedObjectPhase(CFamilyBuildPhase)`: Phase for combining compile and link operations into one phase for building a shared object.
* `class CompileAndLinkToExePhase(CFamilyBuildPhase)`: Phase for combining compile and link operations into one phase for building an executable.
* `class ProjectPhase(Phase)`: Project phase, which represents a full project. You can create multiple projects as dependencies of `get_main_phase()`, each their own subproject with compile and link phases, etc. The top-level phase of a makefile is always a project phase.

An easier view of the class heierarchy:
```
Phase
├── CommandPhase
├── CFamilyBuildPhase
│   ├── CompilePhase
│   ├── ArchivePhase
│   ├── LinkToSharedObjectPhase
│   ├── LinkToExePhase
│   ├── CompileAndArchive
│   ├── CompileAndLinkeToSharedObjectPhase
│   └── CompileAndLinkToExePhase
├── ProjectPhase
```

### Dependencies

As mentioned, dependencies among phases are set in the makefile. There are several things to know about dependency relationships:
* Mostly what dependencies do is generate the files other dependent phases need.
* They cannot be cyclical. The dependency graph must not contain loops, though diamond relationships are fine.
* Option overrides and actions that are specified to multiple phases in a dependency tree happen in reverse depth-first order. The deepest dependency phases act first; this way, dependencies that build objects will happen before those that depend on them to build libraries, etc. When setting actions and overrides from the command line, the default is to set them to all phases, so whole dependency graphs can be levered at once.

If your project has multiple steps to build static libraries or shared objects (dynamic libraries) which are then used by other binaries in the build, you can make them dependencies of the built binary phases that use them. The appropriate directories and file references will automatically be resolved. Further, depnding on the properties of the project, appropriate dynamic lookup options will be inserted as well (like `-rpath` options for UNIX-like systems).

## Actions

Pyke is not just good for building. There are other standard actions it can perform, with more forthcoming. Actually, it's more correct to say that `Phase` objects perform actions. Any string passed as an action on the command line will be applied as an action to the appropriate phases which implement the action. If no phase supports the action, it is quietly ignored.

There is a default action (`report_actions`) which displays the available actions in each phase of a project. This default can be overridden in a config file, either in a project or under $HOME (see [configuring pyke](#configuring-pyke)), to make the default action something different.

### Built-in actions

Currently, the supported actions in each built-in phase are:

|phase class|actions
|---|---
|Phase|clean; clean_build_directory; report_actions; report_files; report_options
|CommandPhase|build; (inherited: clean; clean_build_directory; report_actions; report_files; report_options) 
|CFamilyBuildPhase|(inherited: clean; clean_build_directory; report_actions; report_files; report_options)
|CompilePhase|build; (inherited: clean; clean_build_directory; report_actions; report_files; report_options)
|ArchivePhase|build; (inherited: clean; clean_build_directory; report_actions; report_files; report_options)
|LinkToSharedObjectPhase|build; (inherited: clean; clean_build_directory; report_actions; report_files; report_options)
|LinkToExePhase|build; run; (inherited: clean; clean_build_directory; report_actions; report_files; report_options)
|CompileAndArchivePhase|build; (inherited: clean; clean_build_directory; report_actions; report_files; report_options)
|CompileAndLinkToSharedObjectPhase|build; (inherited: clean; clean_build_directory; report_actions; report_files; report_options)
|CompileAndLinkToExePhase|build; run; (inherited: clean; clean_build_directory; report_actions; report_files; report_options)
|ProjectPhase|(inherited: clean; clean_build_directory) (all other actions are the responsiblity of dependencies)

These can be spcified on the command line. Multiple actions can be taken in succession; see below for CLI operation.

* `report_options` prints a report of all phases and their options and overrides. This is useful to check that your command line overrides are doing what you think.
* `report_files` prints a report of the files that are used and generated by each phase.
* `report_actions` prints a report of all the actions each phase will respond to.
* `clean` specifies that a phase will delete the files it is responsible for making.
* `clean_build_directory` specifies that the entire build directory tree will be deleted.
* `build` is the build action. This generates the build artifacts.
* `run` runs built executables in place. Note that CommandPhase commands happen on the `build` action.

### Action aliases

There are built-in aliases for the defined actions, to save some effort:

|alias|actions
|---|---
|opts|report_options
|files|report_files
|actions|report_actions
|c|clean
|cbd|clean_build_directory
|b|build

### Action mapping

You may wish to associate one action to another. For example, an executable that `build` creates may itself be part of a later `build` action, but it can run only on the `run` action. You can wire up an action to be performed on another action by setting a particular `action map` as an option:

```python
doc_builder = p.CompileAndLinkToExePhase({
    ...
    'action_map': { 'build_docs': [ 'build', 'run' ]},
    ...
})
```

This specifies that, on the `build_docs` action, this phase should run its `do_action_build` method, followed by its `do_action_run` method. This allows for some flexibility in the action set for your makefile, especially if you're using a built-in or 3rd-party phase class.

## Options

Options do not have to be strings. They can be any Python type, really, with the following criteria:

* Options should be *convertible* to strings.
* Options must be copyable (via `copy.deepcopy()`).

We've already seen list-type options, like `sources`, and there are several of those in the built-in phase classes. Custom ANSI colors for output are stored as dictionaries of dictionaries. And of course, any phase class you create can use any new option types you desire, as long as they meet the above criteria.

### Overrides are stacked

When an option is applied to a phase which already has as option by the same name, it is called an `override`. The new option displaces or modifies the existing one, but it does not replace it internally. Rather, it is pushed onto the option's *stack* of values, and can later be *popped* to undo the modification. In this way, an override can, say, remove an entry from an option's listed elements, and later popping of that override will bring it back.

### Override operators

So how does one specify that an override *modifies* an option, instead of *replacing* it? When specifying the name of the option to set with `-o`, you can provide '+=' or '-=' or another operator to specify the modifier. A few option types get special behavior for this syntax:

|original type|operator|override type|effect
|---|---|---|---
|any|=, none|any|the option is replaced by the override
|bool|!=  |bool|logical negation of the boolean value
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

We'll see some examples below.

### Viewing options

The base `Phase` class defines the `report_options` action, with an alias of `opts`. This action prints the phases in depth-first dependency order, and each phase's full set of options in both raw, uninterpolated form, and fully interpolated form. This makes it easy to see what options are available, the type each is set to by default, and how interpolation and override operations are affecting the final result. It's handy for debugging a difficult build.

```
$ pyke opts
name =
     = compile_and_link
     = simple
    -> simple
group = 
      = simple_app
     -> simple_app
report_verbosity: = 2
                 -> 2
report_relative_paths: = True
                      -> True
verbosity: = 0
          -> 0
none: = None
     -> None
true: = True
     -> True
false: = False
      -> False
project_anchor: = /home/schrock/src/pyke/tests/simple_app
              -> /home/schrock/src/pyke/tests/simple_app
gen_anchor: = /home/schrock/src/pyke/tests/simple_app
           -> /home/schrock/src/pyke/tests/simple_app
...
```

Each option is listed with all its stacked raw values, followed by the interpolated value. Notice above that the default value of "verbosity" is set to 0. This makes build actions behave without output (unless there is an error). We can easily see how command-line overrides affect the results. More on how to set them below, but overriding the `verbosity` option with `2` looks like this:

```
$ pyke -o verbosity=2 opts
...
verbosity: = 0
           = 2
          -> 2
...
```

Here, `verbosity` has been overridden, and has a second value on its stack. Subsequent actions will report more information based on the verbosity value.

The detailed report from `report_options` (`opts`) is what you get at `report_verbosity` level `2`. If you want to see only the interpolated values, you can override the `report_verbosity` option to `1`:

```
$ pyke -o report_verbosity=1
name: -> simple
group: -> 
report_verbosity: -> 1
report_relative_paths: -> True
verbosity: -> 0
project_anchor: -> /home/schrock/src/pyke/demos/simple_app
gen_anchor: -> /home/schrock/src/pyke/demos/simple_app
...
```

Like actions, there are argument aliases for some options. `-v2` sets the verbosity to 2, and `-rv1` sets the report_verbosity to 1. There are others as well.

### Interpolation

The details on interpolation are straighforward. They mostly just work how you might expect. A portion of a string value surrounded by `{}` may contain a name, and that name is then used to get the option by that name. The option is converted to a string, if it isn't already (it probably is), and replaces the substring and braces inline, as previously explained. This means that interpolating an option which is a list will expand that list into the string:
```
$ pyke -o formatted_list_of_srcs="'Sources: {sources}'" opts
...
formatted_list_of_sources: = Sources: {sources}
                          -> Sources: ['a.c', 'b.c', 'c.c', 'main.c']
...
```

If the entire value of an option is interpolated, rather than a substring, then the value is replaced entirely by the referenced option, and retains the replacement's type. This is useful for selecting a data structure by name, as explained below.

#### Nested interpolated strings

One useful feature is that interpolations can be nested. `CFamilyBuildPhase` uses this in places to help resolve selectable options. Look carefully at `kind_optimization`'s raw value below. It contains four `{}` sets, two inside the outer, and one nested even deeper. The inner set is interpolated first, and then the outer set according to the new value.

```
$ pyke report
...
kind: = debug
     -> debug
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
optimization: = {{tool_args_{toolkit}}_{kind}_optimization}
             -> 2
...
```

So `optimization` evolves as:

```
optimization: -> {{tool_args_{toolkit}}_{kind}_optimization}
              -> {{tool_args_gnu}_{kind}_optimization}
              -> {gnuclang_{kind}_optimization}
              -> {gnuclang_debug_optimization}
              -> 0
```

Now, when overriding `kind`, a different version of the optimization flags (passed as `-On` to gcc, say) will be automatically interpolated:

```
$ pyke -o kind=release opts
...
kind: = debug
      = release
     -> release
...
optimization: = {{tool_args_{toolkit}}_{kind}_optimization}
             -> 2
...
```

### Overriding in the makefile

When constructing phase objects, the options you declare are technically overrides, if they happen to have the same name as any inherited options. They are treated by default as replacements, though you can provide operators.

You can also explicitly override after phase creation:

```python
from pyke import CompileAndLinkToExePhase, Op, get_main_phase

phase = CompileAndLinkToExePhase('simple_experiemtal', {
    'sources': ['a.cpp', 'b.cpp', 'c.cpp', 'main.cpp'],
    'include_dirs': Op('+=', 'include/exp')        # appending to include_dirs
})

phase.push_opts({                                           # appending to sources
    'sources': Op('*=', [f'exp/{src}' for src in [
             'try_this.cpp', 'maybe.cpp', 'what_if.cpp']])
})

get_main_phase().depend_on(phase)
```

Note the use of the `Op` class, which signals that the override is an operational modifier, not merely a replacement. The operator is expressed as a string. Overriding with a value directly instead of with `Op` implies a replacement ('=').

> Note the difference between *appending* one item to a list with `+=`, as in the phase constructor above, and *extending* multiple items to the list with `*=`, as in the push_opts() call.

You can pop the override with `Phase.pop_opts(key)`.

> `Phase.push_opts` is defined on `Phase` as:
> ```python def push_opts(self, overrides: dict, include_deps: bool = False, include_project_deps: bool = False) ```
> The boolean parameters tell pyke how to propagate overrides through dependency phases. `include_deps` includes dependencies which are not `ProjectPhase`s, and `include_project_deps` includes only `ProjectPhase` phases specifically. Options set in `Phase` constructors call `push_opts` with both set to `False`.

### Overriding on the command line

As seen previously, overrides can be specified on the command line as well with `-o [phases:][option[op value]`. This can look similar to overrides in code (though you may need to enquote it):

```
$ pyke -ocolors=none build
$ pyke -o "compile:sources *= [exp/try_this.c, exp/maybe.c, exp/what_if.c]" opts
```

String values can be in quotes if they need to be disambiguated from punctuation. The usual escapements work with '\'. Overrides you specify with `[]` are treated as lists, `()` as tuples, `{}` as sets, and `{:}` as dicts. Since option keys must only contain letters, numbers, and underscores, you can differentiate a single-valued set from an interpolation by inserting a comma, or specifically enquoting the string:

```
$ pyke -o "my_set_of_one={foo,}" ...
$ pyke -o "my_set_of_one={'foo'}" ...
```

Python's built-in literals True, False, and None are defined as options, and can be interpolated as {true}, {false}, and {none}.

There is more to say about how value overrides are parsed. Smartly using quotes, commas, or spaces to differentiate strings from interpolators will usually get you where you want. Generally, though, setting options in the makefile will probably be preferred.

### Base pyke options

There are a few options that are uiversal to pyke, regardless of the type of project it is running. Here are the options you can set to adjust its behavior:

|option|default|usage
|---|---|---
|name   |''   |The name of the phase. You should likely override this.
|group   |''   |The group name of the phase. Informed by its nearest dependent project phase.
|report_verbosity   |2   |The verbosity of reporting. 0 just reports the phase by name; 1 reports the phase's interpolated options; 2 reports the raw and interpolated options.
|report_relative_paths   |True   |Whether to print full paths, or relative to $CWD when reporting.
|verbosity   |0   |The verbosity of non-reporting actions. 0 is silent, unless there are errors; 1 is an abbreviated report; 2 is a full report with all commands run.
|none   |None   |Interpolated value for None.
|true   |True   |Interpolated value for True.
|false   |False   |Interpolated value for False.
|project_anchor   |project_root   |This is an anchor directory for other directories to relate to when referencing required project inputs like source files.
|gen_anchor   |project_root   |This is an anchor directory for other directories to relate to when referencing generated build artifacts like object files or executables.
|build_dir   |'build'   |Top-level build directory.
|colors_24bit   |color_table_ansi_24bit   |24-bit ANSI color table.
|colors_8bit   |color_table_ansi_8bit   |8-bit ANSI color table.
|colors_named   |color_table_ansi_named   |Named ANSI color table.
|colors_none   |color_table_none   |Color table for no ANSI color codes.
|colors_dict   |'{colors_{colors}}'   |Color table accessor based on {colors}.
|colors   |supported_terminal_colors   |Color table selector. 24bit|8bit|named|none
|action_map   |{}   |Routes action invocations to action calls.
|toolkit   |'gnu'   |Select the system build tools. gnu|clang
|kind   |'debug'   |Sets debug or release build. You can add your own; see the README.
|version_major   |'0'   |Project version major value
|version_minor   |'0'   |Project version minor value
|version_patch   |'0'   |Project version patch value
|version_build   |'0'   |Project version build value
|version   |'{version_mmp}'   |Dotted-values version string.

When running pyke from a directory that is different from your makefile's directory, you can specify the makefile path with `-m`. This is discussed below, but by default both the project root directory (`project_anchor`) and generated output root directory (`gen_anchor`) are relative to the makefile's directory, regardless of where you invoke from. However, this behavior can be modified. By overriding `gen_anchor` to a different directory in your file system, you can cause all the generated outputs to be placed anywhere. The generated directory structure remains the same, just at a different root location. Note that intermediate files which are inputs of later phases, like compiled object files, are still resolved correctly, as *any* generated file is rooted by `gen_anchor`. Likewise, any file that is expected as part of the project inputs created by developers (anything you might check in to your project repository, say) is anchored by `project_anchor`.

If you don't want your makefile to be situated at the project root, overriding `project_anchor` (possibly in the makefile itself) to the actual project root will line things up.

### C/C++ specific options

Pyke began as a build tool for C and C++ style projects. The requisite classes are those that derive from `CFamilyBuildPhase`, and have lots of options for controlling the build. Note that since clang and gcc share much of the same command arguments, their toolchain-specific arguemts are often combined into a single definition.

|option|default|usage
|---|---|---
|language   |'c++'   |Sets the source language. c|c++
|language_version   |'23'   |Sets the source language version.
|gnuclang_warnings   |['all', 'extra', 'error']   |Sets the warning flags for gnu and clang tools.
|gnuclang_debug_debug_level   |'2'   |Sets the debug level (-gn flga) for gnu and clang tools when in debug mode.
|gnuclang_debug_optimization   |'g'   |Sets the optimization level (-On flag) for gnu and clang tools when in debug mode.
|gnuclang_debug_flags   |['-fno-inline', '-fno-lto', '-DDEBUG']   |Sets debug mode-specific flags for gnu and clang tools.
|gnuclang_release_debug_level   |'0'   |Sets the debug level (-gn flga) for gnu and clang tools when in release mode.
|gnuclang_release_optimization   |'2'   |Sets the optimization level (-On flag) for gnu and clang tools when in release mode.
|gnuclang_release_flags   |['-DNDEBUG']   |Sets release mode-specific flags for gnu and clang tools.
|gnuclang_additional_flags   |[]   |Any additional compiler flags for gnu and clang tools.
|definitions   |[]   |Macro definitions passed to the preprocessor.
|posix_threads   |False   |Enables multithreaded builds for gnu and clang tools.
|relocatable_code   |False   |Whether to make the code position-independent (-fPIC for gnu and clang tools).
|rpath_deps   |True   |Whether to reference dependency shared objects with -rpath.
|moveable_binaries   |True   |Whether to condition the build for dependencies which can be relatively placed. (-rpath=$ORIGIN)
|include_dirs   |['include']   |List of directories to search for project headers, relative to {include_anchor}.
|sources   |[]   |List of source files relative to {src_anchor}.
|lib_dirs   |[]   |List of directories to search for library archives or shared objects.
|libs   |{}   |Collection of library archives or shared objects or pkg-configs to link. Format is: { 'foo', type } where type is 'archive' | 'shared_object' | 'package'
|prebuilt_obj_dir   |'prebuilt_obj'   |Specifies the directory where prebuilt objects (say from a binary distribution) are found.
|prebuilt_objs   |[]   |List of prebuilt objects to link against.
|build_detail   |'{group}.{toolkit}.{kind}'   |Target-specific build directory.
|obj_dir   |'int'   |Directory where intermediate artifacts like objects are placed.
|obj_basename   |''   |The base filename of a taret object file.
|posix_obj_file   |'{obj_basename}.o'   |How object files are named on a POSIX system.
|thin_archive   |False   |Whether to build a 'thin' archive. (See ar(1).)
|archive_dir   |'lib'   |Where to emplace archive library artifacts.
|archive_basename   |'{name}'   |The base filename of a target archive file.
|posix_archive_file   |'lib{archive_basename}.a'   |How archives are named on a POSIX system.
|rpath   |{}   |Collection of library search paths built into the target binary. Formatted like: { 'directory': True } Where the boolean value specifies whether to use $ORIGIN. See the -rpath option in the gnu and clang tools. Note that this is automatically managed for dependency library builds.
|shared_object_dir   |'lib'   |Where to emplace shared object artifacts.
|shared_object_basename   |'{name}'   |The base filename of a shared object file.
|generate_versioned_sonames   |False   |Whether to place the version number into the artifact, and create the standard soft links.
|so_major   |'{version_major}'   |Shared object major version number.
|so_minor   |'{version_minor}'   |Shared object minor version number.
|so_patch   |'{version_patch}'   |Shared object patch version number.
|posix_so_linker_name   |'lib{shared_object_basename}.so'   |How shared objects are unversioned-naemd on POSIX systems.
|posix_so_soname   |'{posix_so_linker_name}.{so_major}'   |How shared objects are major-version-only named on POSIX systems.
|posix_so_real_name   |'{posix_so_soname}.{so_minor}.{so_patch}'   |How shared objects are full-version named on POSIX systems.
|posix_shared_object_file   |'{posix_so_linker_name}'   |The actual target name for a shared object. May be redefined for some project types.
|exe_dir   |'bin'   |Where to emplace executable artifacts.
|exe_basename   |'{name}'   |The base filename of a target executable file.
|posix_exe_file   |'{exe_basename}'   |How executable files are named on POSIX systems.
|run_args   |''   |Arguments to pass when running a built executable.

### Making sense of the directory optinos

Each of the include, source, object, archive, static_object and executable directories are built from components, some of which you can change to easily modify the path. Pyke is opinionated on its default directory structure, but you can set it how you like.

#### Include files
```
inc_dir = .
include_anchor = {project_anchor}/{inc_dir}/\<include directory\>
include_dirs = [include]
```
You are encouraged to change `inc_dir` to set a base directory for all include directories. Pyke will reference `include_anchor` and `include_dirs` directly when building command lines; `inc_dir` is just there to construct the path.

#### Source files
```
src_dir = src
src_anchor = {project_anchor}/{src_dir}
```
You are encouraged to change `src_dir` to set a base directory for all the source files. Note that there is only a single source directory specified. Pyke does not search for named files; rather, you need to explicitly specify each source's directory or path.

#### Build base directory structure
```
build_dir = build
build_detail = {kind}.{toolkit}
build_anchor = {gen_anchor}/{build_dir}
build_detail_anchor = {build_anchor}/{build_detail}
```
You are encouraged to change `build_dir` to set a different base for generated files, and `build_detail` to control different buld trees. Pyke will reference `build_detail_anchor` and `build_dir` directly.

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

Similar options are defined for static archives and shared objects. Of course, you can change any of these, or make your own constructed paths.

## The CLI

The general form of a pyke command is:

```
pyke [-v | -h | [-c]? [-m makefile]? ]? [[-p [phase[,phase]*]]* | [-o [phase[,phase]*:]key[op_value]]* | [phase[,phase]*:][action]* ]*
```

Notably, -o and action arguments are processed in command-line order. You can set the phases to use with each, setting some option overrides, performing actions, setting different options, perform more actions, etc. If no phases are specified, the overrides and actions apply to all phases, in reverse depth-first dependency order.

The command line arguments are:
* `-v`, `--version`: Prints the version information for pyke, and exits.
* `-h`, `--help`: Prints a help document.
* `-c`, `--cache_makefile`: Allows the makefile's __cache__ to be generated. This might speed up complex builds, but they'd hvae to be really complex. Must precede any arguments that are not -v, -h, or -m.
* `-m`, `--module`: Specifies the module (pyke file), or its directory if the pyke file is called 'make.py', to be run. Must precede any arguments that are not -v, -h, or -c. If no -m argument is given, pyke will look for and run ./make.py.
* `-p`, `--phases`: Specifies a subset of phases on which to apply subsequent overrides or actions, if such arguments do not provide their own. Each `-p` encountered resets the subgroup. Option and action arguments that provide their own phases overrule `-p` for that argument, but do not reset it.
* `-o`, `--override`: Specifies an option override to apply to some or all phases for subsequenet actions. If the option is given as a key-op-value, the override is pushed; if it is only a key (with no operator-value pair) the override is popped.
* `action`: Arguments given without switches specify actions to be taken on the indicated phases. Any action on any phase which doesn't support it is quietly ignored.

### Referencing phases

Phases have names (`short name`s), as seen, but also have `full name`s, given as "group.name". For each phase, if the group name is not explicitly set, it is overridden *after the makefile is run* to be the short name of the closest dependency *project phase*. Project phases are thereafter given the short name `project`. This naming scheme allows for subprojects to be referenced by the group name on the CLI. We'll see some examples.

The main project group is named according to the name of the makefile, unless it is specifically called `make.py`, in which it is name of the directory in which it resides. So, if your project's root contins the makefile, and is named like this:
```
~/src/asset_converter/make.py
```
The project will be called "asset_converter.project". If, however, it is named like:
```
~/src/asset_converter/images_make.py
```
The project will be called "images_make.project".

Dependency phases of any project phase which are not themselves project phases are specified by the dotted name. Maybe your `asset_converter` project has dependencies like this:

```
asset_converter (ProjectPhase)
├── image_converter (ProjectPhase)
│   └── link (LinkToExePhase)
│       ├── compile_jpg (CompilePhase)
│       ├── compile_png (CompilePhase)
│       └── compile_tga (CompilePhase)
└── mesh_converter (ProjectPhase)
    └── link (LinkToExePhase)
        ├── compile_blender (CompilePhase)
        ├── compile_3ds (CompilePhase)
        └── compile_dxf (CompilePhase)
```

Here, each phase will be fully named by its owning project phase and its non-project phase names:
* `asset_converter.project`
* `image_converter.project`
* `image_converter.link`
* `image_converter.compile_jpg`
* `image_converter.compile_png`
* `image_converter.compile_tga`
* `mesh_converter.project`
* `mesh_converter.link`
* `mesh_converter.compile_blender`
* `mesh_converter.compile_3ds`
* `mesh_converter.compile_dxf`

When referencing phases on the command line, you can always reference by full name. For convenience, you can omit the group name of the main project, and it will be implied. An @ symbol references all the phases in either the group, short name, or both. So, for simple_app, you can reference just the compile phase like:

```
pyke -o compile:verbosity=2
pyke -o .compile:verbosity=2
pyke -o simple_app.compile:verbosity=2
```

By default, if the phase names are not specified at all, then all phases are affected. In actuality, it uses phase name "@.@", and is usually what you'd want. For complicated projects with multiple ProjectPhases, each can be separately referenced precisely.

```
pyke -okind=release -oimage_converter.@:kind=debug build
```

The above performs a release build for most of the project, but a debug build for only the image_converter subproject. If you want to just build image_converter:

```
pyke image_converter.@:build
```

Note that the naming is *not* strictly hierarchical, but rather, specifically `group.name`. Phases must always be uniquely named within a project (and will be automatically disambiguated if they're not).

## Configuring pyke

Pyke has an internal cnofig which provides some convenient aliases. On startup, once pyke has found the makefile but before it is loaded, pyke looks for additional configs in the following order:
* ~/.config/pyke/pyke-config.json
* <makefile's directory>/pyke-config.json

An example config might look like this:

```json
{
    "argument_aliases": {
        "-noc": "-ocolors=none",
        "-bdb": "dbadmin:build",
        "-rdb": [
            "-odbadmin:run_args=\"-logging=TRUE -username=$DBADMIN_UNAME -password=$DBADMIN_PASSWD\"",
            "dbadmin:run"
        ]
    },
    "action_aliases": {
        "pf": "package_flatpak",
        "vac": "verify_appchecker"
    },
    "default_action": "build",
    "default_arguments": [
        "-v2"
    ]
}
```

Each can contain the following sections:

### Argument aliases

These are convenient shorthands for complex overrides, override-action pairs, or whatever you like. Their values cannot contain other argument alias names, but *can* contain action aliases, and are otherwise exactly as you'd type them on the CLI (except you don't need to enquote things that the shell might interpret). Multiple values must be housed in a list. Each config file adds to the list of argument aliases.

### Action aliases

Actions can be aliased. These are one-for-one word replacements, and the action values must not be other action aliases, though you *can* have more than one alias for any given action. Each config file adds to the list of action aliases.

### Default action

The default action is taken when no action is specified on a CLI. By default, this is set to `report_actions`. The value must not be an alias. Each config file overrides a set default action.

### Default arguments

Ccontains a list of strings, each of which is a separate command line argument. These can be full names or aliases. They are placed consecutively directly after the -m argument, but before any -o or action arguments, on every invocation of pyke. It is a convenient way to customize the way pyke always works on your project or machine. Each config file appends to the list of default arguments.

## Advanced Topics

### Adding new phases

Of course, a benefit of a programmatic build system is extension. Building your own Phase classes shold be straightforward. You likely won't have to often.

Say you need a code generator. It must make .c files your project compiles and links with extant source. You can write a custom Phase-derived class to do just this. This gets you into the weeds of `Step` and `Result` classes, and action steps. More help will be provided in the future, but for now, let's just look at the code in demos/custom_phase/custom.py:

```python
''' Custom phase for pyke project.'''

from functools import partial
from pathlib import Path
from pyke import (CFamilyBuildPhase, Action, ResultCode, Step, Result, FileData,
                  input_path_is_newer, do_shell_command)

class ContrivedCodeGenPhase(CFamilyBuildPhase):
    '''
    Custom phase class for implementing some new, as-yet unconcieved actions.
    '''
    def __init__(self, options: dict | None = None, dependencies = None):
        super().__init__(options, dependencies)
        self.options |= {
            'name': 'generate',
            'gen_src_dir': '{build_anchor}/gen',
            'gen_src_origin': '',
            'gen_sources': {},
        }
        self.options |= (options or {})

    def get_generated_source(self):
        ''' Make the path and content of our generated source. '''
        return { Path(f"{self.opt_str('gen_src_dir')}/{src_file}"): src
                 for src_file, src in self.opt_dict('gen_sources').items() }

    def compute_file_operations(self):
        ''' Implelent this in any phase that uses input files or generates output files.'''
        for src_path in self.get_generated_source().keys():
            self.record_file_operation(
                None,
                FileData(src_path.parent, 'dir', self),
                'create directory')
            self.record_file_operation(
                FileData(Path(self.opt_str('gen_src_origin')), 'generator', self),
                FileData(src_path, 'source', self),
                'generate')

    def do_step_generate_source(self, action: Action, depends_on: list[Step] | Step | None,
                                source_code: str, origin_path: Path, src_path: Path) -> Step:
        ''' Performs a directory creation operation as an action step. '''
        def act(cmd: str, origin_path: Path, src_path: Path):
            step_result = ResultCode.SUCCEEDED
            step_notes = None
            if not src_path.exists() or input_path_is_newer(origin_path, src_path):
                res, _, err = do_shell_command(cmd)
                if res != 0:
                    step_result = ResultCode.COMMAND_FAILED
                    step_notes = err
                else:
                    step_result = ResultCode.SUCCEEDED
            else:
                step_result = ResultCode.ALREADY_UP_TO_DATE

            return Result(step_result, step_notes)

        cmd = f'echo "{source_code}" > {src_path}'
        step = Step('generate source', depends_on, [origin_path],
                    [src_path], partial(act, cmd=cmd, origin_path=origin_path, src_path=src_path),
                    cmd)
        action.set_step(step)
        return step

    def do_action_build(self, action: Action):
        ''' Generate the source files for the build. '''
        def get_source_code(desired_src_path):
            for src_path, src in self.get_generated_source().items():
                if src_path == desired_src_path:
                    return src.replace('"', '\\"')
            raise RuntimeError('Cannot find the source!')

        dirs = {}
        all_dirs = [fd.path for fd in self.files.get_output_files('dir')]
        for direc in list(dict.fromkeys(all_dirs)):
            dirs[direc] = self.do_step_create_directory(action, None, direc)

        origin_path = Path(self.opt_str('gen_src_origin') or __file__)

        for file_op in self.files.get_operations('generate'):
            for out in file_op.output_files:
                source_code = get_source_code(out.path)
                self.do_step_generate_source(action, dirs[out.path.parent],
                                             source_code, origin_path, out.path)
```

There's a bit going on, but it's not terrible. This uses some facilities available in `CFamilyBuildPhase` to clean generated source and the generation directory, as well as making directories for the build. The main work is in generating the source files in an appropriate generation directory.

Integrating this custom phase into your makefile is as simple as making a new instance of the new phase, and setting it as a dependency of the build phase:

```python
'Bsic project with custom code generation phase'

# pylint: disable=wrong-import-position

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from custom import ContrivedCodeGenPhase
import pyke as p

gen_src = {
'd.c': r'''
#include "abc.h"

int d()
{
    return 1000;
}''',

'e.c': r'''
#include "abc.h"

int e()
{
	return 10000; 
}'''
}

gen_phase = ContrivedCodeGenPhase({
    'gen_src_origin': __file__,
    'gen_sources': gen_src,
})

build_phase = p.CompileAndLinkToExePhase({
    'name': 'simple',
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
}, gen_phase)

p.get_main_phase().depend_on(build_phase)
```

And that's it. Now the `build` action will first generate the files in the right place if needed, and then build them if needed. The `clean` action will delete the generated files, and the `clean_build_directory` action will not only remove the build, but also the generated source directory.

> A few notes: The above will only generate the source files if they don't exist, or are older than the makefile (which has the source text in it). Also, the gen diretory is based on `gen_anchor` (by way of `build_anchor`), which is necessary for any generated files to be built in the right place if you change `gen_anchor`'s value.

#### Adding new actions

To add a new action to a custom phase, simply add a method to the phase class. For example, to add an action called "deploy", write a method like so:

```python
    def do_action_deploy(self, action: Action) -> ResultCode:
        ...
```
(You'll want to import Action and ResultCode from pyke if you want the annotations.) That's all you need to do for the method to be called on an action, since actions' names are just strings, and pyke reflects on method names to find a phase that can handle the action. Of course, implmenting actions is more involved, as you can see above.

### Adding new build kinds

Adding new build kinds is straightforward if you're just trying to customize the system build commands. There are currently three that depend on the build kind: `debug_level`; `optimization`; and `flags`. For POSIX tools, these correspond to the `-g{debug_level}`, `-O{optimization}`, and `{flags}` of any definition. If you wanted a custom kind called "smallest", imply provide the following overrides, with perhaps these values:

```
'gnuclang_smallest_debug_level': '0',
'gnuclang_smallest_optimization': 's',
'gnuclang_smallest_flags': ['-DNDEBUG'],
```

When selecting the build kind with `-o kind=smallest`, these overrides should be selected for the build.

### Setting colors

The colorful output can be helpful, but not if you're on an incapable terminal, or just don't like them or want them at all. You can select a color palette:

```
pyke -o colors=none build
pyke -o colors=named build
pyke -o colors=8bit build
pyke -o colors=24bit build
```

Defining your own color palette is possible as well. You'll want to define all the named colors:

```
pyke -o colors_custom="{ off: {form:off}, success: {form:b24, fg:[0,255,0], bg:[0,0,0]}, ...}" -o colors=custom build
```

That gets cumbersome. You can change an individual color much more easily:

```
pyke -o "colors_24bit|={shell_cmd: {form:b24, fg:[255, 255, 255]}}"
```

These are likely best set as default arguments in `$HOME/.config/pyke/pyke-config.json`. (See [configuring pyke](#configuring-pyke).):

```json
{
    "default_arguments": [
        "-o colors_super =  { off:              { form: off }}",
        "-o colors_super |= { success:          { form: b24, fg: (0x33, 0xaf, 0x55) }}",
        "-o colors_super |= { fail:             { form: b24, fg: (0xff, 0x33, 0x33) }}",
        "-o colors_super |= { phase_lt:         { form: b24, fg: (0x33, 0x33, 0xff) }}",
        "-o colors_super |= { phase_dk:         { form: b24, fg: (0x23, 0x23, 0x7f) }}",
        "-o colors_super |= { step_lt:          { form: b24, fg: (0xb3, 0x8f, 0x4f) }}",
        "-o colors_super |= { step_dk:          { form: b24, fg: (0x93, 0x5f, 0x2f) }}",
        "-o colors_super |= { shell_cmd:        { form: b24, fg: (0x31, 0x31, 0x32) }}",
        "-o colors_super |= { key:              { form: b24, fg: (0x9f, 0x9f, 0x9f) }}",
        "-o colors_super |= { val_uninterp_lt:  { form: b24, fg: (0xaf, 0x23, 0xaf) }}",
        "-o colors_super |= { val_uninterp_dk:  { form: b24, fg: (0x5f, 0x13, 0x5f) }}",
        "-o colors_super |= { val_interp:       { form: b24, fg: (0x33, 0x33, 0xff) }}",
        "-o colors_super |= { token_type:       { form: b24, fg: (0x33, 0xff, 0xff) }}",
        "-o colors_super |= { token_value:      { form: b24, fg: (0xff, 0x33, 0xff) }}",
        "-o colors_super |= { token_depth:      { form: b24, fg: (0x33, 0xff, 0x33) }}",
        "-o colors_super |= { path_lt:          { form: b24, fg: (0x33, 0xaf, 0xaf) }}",
        "-o colors_super |= { path_dk:          { form: b24, fg: (0x13, 0x5f, 0x8f) }}",
        "-o colors_super |= { file_type_lt:     { form: b24, fg: (0x63, 0x8f, 0xcf) }}",
        "-o colors_super |= { file_type_dk:     { form: b24, fg: (0x43, 0x5f, 0x9f) }}",
        "-o colors_super |= { action_lt:        { form: b24, fg: (0xf3, 0x7f, 0x0f) }}",
        "-o colors_super |= { action_dk:        { form: b24, fg: (0xa3, 0x4f, 0x00) }}",
        "-o colors=super"
    ]
}
```

The above colors are the default for 24-bit RGB colors. Change them however you like.

An individual color has the format:

```
{form: <format>, fg: <foreground-color>, bg: <background-color>}
```

For b24 formats, each of fg and bg should specify a tuple of red, green, blue, from 0 through 255. For b8 formats, each of fg and bg should specify a single integer [0, 255] which matches the ANSI 8-bit color palette. For the named formats, the ANSI named colors are used, like 'red' and 'bright blue'. If you want to specify no color, leave the color dict empty. The 'off' color dict is special, and must be kept as '{form: off}'.
