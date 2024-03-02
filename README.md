# pyke

Pyke is a python-based, extensible system for building and operating software projects. Its first functions centered around cleaning and building C and C++ projects, but it can do much more. Future development work will expand languages and environments in which pyke can be useful, actions such as running, installing, deploying and testing, and will support a plugin interface for expansion beyond the core.

## The rationale

Pyke is being designed to act initially as an alternative to CMake. I'm not expert in CMake, and many of the below may also apply to it, but I wanted to build pyke as a personal project, and use it in other projects of my own.

- Minimal artifacts
Within a project, the only artifacts that result from a build operation are the intermediate files from the build itself (.o files, specifically, for C-family projects) and the final output. The only necessary support file in a project is the make.py file itself, probably at the project root folder.

- Flexibility
Of course, the pyke project file doesn't have to be at the root of a project. And it doesn't have to be called make.py. A pyke file can specify specific anchor directories for project files and generated artifacts. Command-line overrides can modify them in times of need.

- Just-beyond-declarative configuration.
Usually, a declarative syntax is desireable for systems like this. But even CMake is a sort of language, and pyke files are too--just, in python. Very basic python is all you need to know to use it fully, and when you need that convenience of a full language, it's very nice to have. Sane defaults and a simple object structure help keep things somewhat minimal for a basic build.

- Extensibility
Pyke comes with some basic classes (called Phases) which can manage basic tasks. But you may have special needs in your project tha require a specific tool to be run, or files to be moved around, or secret keys to be managed, etc. If it's not in the basic set of classes, build your own. It's a reasonable interface to design new functionality for.

Eventually there will be a plugin interface for separate extension projects. This is still being designed, and the basic builtin classes are being fleshed out now.

## Installing pyke

Couldn't be easier. You need to be running python3.10 at least, and have pip installed. To install it globally:

```bash
$ pip install pyke

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

where build/release.gnu/bin/simple is the final binary executable.

Of course, this is a very minimal example, and much more configuration is possible. 
