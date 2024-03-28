''' Action map -- maps inputs to outputs, across all phases of a project.'''
# pylint: disable=too-few-public-methods

from enum import Enum
from .phases import Phase
from .utilities import ensure_list

X = '''
file_in -> file_out         action: phase, action_name, action_ordinal, time, duration, was already
                            file: type, {system | project | generated from other phase f |
                                generated from other project p | generated from this phase},
                                is already done
'''

class FileOrigin(Enum):
    ''' File origin enum. Maybe make this a base class for extensibility?'''
    SYSTEM = 0

class FileType:
    ''' File type. Base class for extensibiliy.'''
    def __init__(self, extensions):
        self.extensions = ensure_list(extensions)

class CFile(FileType):
    ''' C file type.'''
    def __init__(self):
        super().__init__(['c'])

class CppFile(FileType):
    ''' C file type.'''
    def __init__(self):
        super().__init__(['C', 'cc', 'cpp', 'CPP', 'C++', 'c++'])

class CHeader(FileType):
    ''' C header file type.'''
    def __init__(self):
        super().__init__(['h'])

class CppHeader(FileType):
    ''' C++ header file type.'''
    def __init__(self):
        super().__init__(['h', 'hpp', 'H', 'h++', 'inl'])

class ObjectFile(FileType):
    ''' C file type.'''
    def __init__(self):
        super().__init__(['o', 'obj'])

class ExecutableFile(FileType):
    ''' Executable type.'''
    def __init__(self):
        super().__init__(['exe', ''])

class ActionMap:
    ''' Maps files to files via actions. This serves several purposes, from phase-to-phase file
        discovery, project-to-project file discovery, detailed reporting, simulation. Almost like
        a database, it tracks what files are sourced and generated via various actions, and the
        results of the last run of such actions.'''
    def __init__(self):
        self.files = {}
        self.actions = []

class FileData:
    ''' Describes a file, in terms of its origin, type, use as inputs, etc.'''
    def __init__(self, path: str):
        self.path = path
        self.origin: FileOrigin
        self.actions = []

class ActionData:
    ''' Describes actions used to read or generate files.'''
    def __init__(self):
        self.phase: Phase = None
        self.action_name: str = ''

        self.action_ordinal: int = -1
        self.time: int = 0
        self.duration: int = 0
        self.was_already_done: bool = False
