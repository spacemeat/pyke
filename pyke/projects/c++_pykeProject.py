from .default_pykeProject import Project

class CPlusPlusProject (Project):
  def __init__(self, path, data):
    super().__init__(path, data)
  
  def doCommandOverride(self, command):
    if command == 'clean':
      print ("Cleaning.")
      return True
    else:
      return super().doCommandOverride(command)
  
def makeProject(path, data):
  return CPlusPlusProject(path, data)
