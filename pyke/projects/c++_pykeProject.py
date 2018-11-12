from .default_pykeProject import Project
from ..PykeError import PykeError
from ..tools.Tool import makeNewTool
from ..tools.CPlusPlusTool import CPlusPlusTool


class CPlusPlusProject (Project):
  def __init__(self, path, data):
    super().__init__(path, data)
    self.toolSet = makeNewTool(self)
    if not isinstance(self.toolSet, CPlusPlusTool):
      raise PykeError('toolSet must reference a subtype of CPlusPlus')


  def doCommandOverride(self, command):
#    print (self.data)
    if command == 'clean':
      self.doClean()
      return True
    elif command == 'build':
      self.doBuild()
      return True
    else:
      return super().doCommandOverride(command)
  

  def doClean(self):
    self.toolSet.cleanProject()


  def doBuild(self):
    self.toolSet.buildProject()

  
def makeProject(path, data):
  return CPlusPlusProject(path, data)
