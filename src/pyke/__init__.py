"""
Defining the pyke module.
"""

from .options import Options, OptionOp, Op
from .phases import (Phase, CFamilyBuildPhase, CompilePhase, ArchivePhase, LinkToExePhase,
                     LinkToSharedObjectPhase, CompileAndArchivePhase, CompileAndLinkToExePhase,
                     CompileAndLinkToSharedObjectPhase, ProjectPhase)
from .pyke import get_main_phase
from .action import Action, ResultCode, Step, Result, FileData
from .utilities import input_path_is_newer, do_shell_command
