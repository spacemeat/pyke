from pyke.PykeError import PykeError
from .Tool import Tool
from ansiTerm.ansiTerm import ansiTerm as t


class CPlusPlusTool(Tool):
  def __init__(self, project):
    super().__init__(project)


  def cleanProject(self):
    raise PykeError('cleanProject() needs an implementation.')


  def buildProject(self):
    raise PykeError('buildProject() needs an implementation.')

