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
    'sources': ['a.c', 'b.c', 'c.c', 'main.c'],
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
    ├── a.c
    ├── b.c
    ├── c.c
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

> It should be noted that most of these options so far are actually contained in a `Phase`-derived class called `BuildPhase`. This is because several different `BuildPhase`-derived classes make use of the same options. It works just the same, as derived phase class inherit their supers' options.

## Phases

Phases represent the transformation of files--inputs to outputs. Any useful build phase will have input files and output files. Some of these may be source, authored by developers. Some may be created by compiling source to object, linking objects to executables or libraries, cloning repos, or running code generation tools. When the outputs of one phase are the inputs of another, the one is a `dependency` of the other. Dependencies are set in the makefile explicitly, but their output->input mechanistry is automatic once set.

A specific phase may be invoked on the command line with `-p phase`, but this is optional. If a phase is not specified, then the *last* phase passed to `pyke.use_phases()` is the default phase.

Each operation of a build may have a dedicated phase. C/C++ builds that are more complex than `simple` above are likely to have a `CompilePhase` instance dedicated to each single source file->object file transformation. Phases can be cloned, and their options as set at the time of cloning are copied with them. So, a template `CompilePhase` can be preset, and each clone made have its requisite source file set to `src`. Each `CompilePhase` object would then be set as a dependency of a `LinkPhase` object, which will automatically gather the generated object files from each `CompilePhase` for linking. Such an example makefile might look like this (with an additional few source files in a differnt directory, for spice):

```python
'''multiphase cloned simple'''

import pyke as p

c_to_o_phases = []

proto = p.CompilePhase({})

for src in ('a.c', 'b.c', 'c.c', 'main.c'):
    c_to_o_phases.append(proto.clone({'name': f'compile_{src}', 'sources': [src]}))

proto = p.CompilePhase({
    'src_dir': 'exp',
    'obj_dir': 'int/exp',
})

for src in ('a.c', 'b.c'):
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
* `class BuildPhase(Phase)`: Common base class for building C and C++ projects.
* `class CompilePhase(BuildPhase)`: Phase for compiling a single source file to a single object file.
* `class LinkPhase(BuildPhase)`: Phase for linking objects together to form a final archive, shared object, or executable binary.
* `class CompileAndLinkPhase(BuildPhase)`: Phase for combining compile and link operations into one phase, perhaps with a single call to the native build tool.

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
|BuildPhase|clean; build
|CompilePhase|clean; build
|LinkPhase|clean; build
|CompileAndBuildPhase|clean; build

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

TODO: some examples here

### Viewing options

The base `Phase` class defines the `report` action. This action prints the phases in depth-first dependency order, and each phase's full set of options in both raw, uninterpolated form, and fully interpolated form. This makes it easy to see what options are available, the type each is set to by default, and how interpolation and override operations are affecting the final result. It's handy for debugging a difficult build.

```bash
$ pyke report
```
```
phase: simple
name: = ~~unnamed~~
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

Each option is listed with all its stacked raw values, followed by the interpolated value. Notice above that the default name, "unnamed", is overridden by a replacement operation (`=`) with "simple". You can also easily see how command-line overrides are affecting the results. More on how to set them below, but it looks like this:

```bash
$ pyke -o name:less_simple report
```
```
phase: less_simple
name: = ~~unnamed~~
      = ~~simple~~
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

Here again, `name` has been overridden, this time by the command line.

### Interpolation

The details on interpolation are straighforward. They mostly just work how you might expect. A portion of a string value surrounded by `'{''}'` may contain a name, and that name is then used to get the option by that name. The option is converted to a string, if it isn't already (it probably is), and replaces the substring and braces inline, as previously explained. This means that interpolating an option which is a list will expand that list into the string:
```bash
$ pyke -o "list_of_srcs:Sources: {sources}" report
...
list_of_srcs: = Sources: {sources}
              = Sources: ['a.c', 'b.c', 'c.c', 'main.c']
...
```

If the entire value of an option is interpolated, rather than a substring, then the value is replaced entirely by the referenced option, and retains the replacement's type. This is useful for selecting a data structure by name, as explained below.

#### Nested interpolated string

One useful feature is that interpolations can be nested. `BuildPhase` uses this in places to help resolve selectable options. Look carefully at `kind_optimization`'s raw value below. It contains two '{''}' sets, one inside the other. The inner set is interpolated first, and then the outer set according to the new value.

```bash
$ pyke report
```
```
...
kind: = release
     -> release
...
debug_optimization: = 0
                   -> 0
...
release_optimization: = 2
                     -> 2
...
kind_optimization: = {{kind}_optimization}
                  -> 2
...
```

Now, when overriding `kind`, a different version the optimization flags (passed as -O to gcc, say) will be automatically interpolated:

```bash
$ pyke -o kind:debug report
```
```
...
kind: = ~~release~~
      = debug
     -> debug
...
kind_optimization: = {{kind}_optimization}
                  -> 0
...
```

### Overriding in make.py

### Overriding on the command line

### C/C++ specific options

## The CLI

## Advanced Topics

### Simulating the run

### Adding new phases

#### Adding new actions

### Setting colors

### Anchors



