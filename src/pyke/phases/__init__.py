''' The phases directory imports. '''

from .phase import Phase
from .command_phase import CommandPhase
from .c_family_build import CFamilyBuildPhase
from .compile import CompilePhase
from .archive import ArchivePhase
from .link_to_shared_object import LinkToSharedObjectPhase
from .link_to_exe import LinkToExePhase
from .compile_and_archive import CompileAndArchivePhase
from .compile_and_link_to_exe import CompileAndLinkToExePhase
from .compile_and_link_to_so import CompileAndLinkToSharedObjectPhase
from .project import ProjectPhase
