"""
Defining the pyke module.
"""

try:
    from ._version import version as __version__
    from ._version import version_tuple
except ImportError:
    __version__ = '(unknown version)'
    version_tuple = (0, 0, '(unknown version)')

from .action import Action, ResultCode, Step, Result, FileData
from .options import Options, OptionOp, Op
from .options_owner import OptionsOwner
from .phases import (Phase, CommandPhase, CFamilyBuildPhase, CompilePhase, ArchivePhase,
                     LinkToExePhase, LinkToSharedObjectPhase, CompileAndArchivePhase,
                     CompileAndLinkToExePhase, CompileAndLinkToSharedObjectPhase, ProjectPhase,
                     ExternalRepoPhase, PykeRepoPhase, CMakeRepoPhase)
from .pyke import get_main_phase, PykeExecutor, run_makefile
#from .sync_external_repo import sync_external_repo
from .utilities import input_path_is_newer, do_shell_command
