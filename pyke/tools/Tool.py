import os
import importlib
from pyke.timer import timer
from ansiTerm.ansiTerm import ansiTerm as t


def makeNewTool(project):
  #print (f'Using sys.path = {sys.path}')
  m = importlib.import_module(
    ''.join(['pyke.tools.pykeTools_', project.data.get("toolSet")]))
  nt = m.makeTool(project)

  return nt


class Tool():
  def __init__(self, project):
    self.project = project
    

  def _doShellCommandList(self, cmds):
    for cmd in cmds:
      compProc = self._doShellCommand(cmd)
  

  def _doShellCommand(self, command):
    t.print(f'<!shellCommand>{command}<!/>')
    timer.start(f'Shell command {command[:20]}...')
    try:
      compProc = subprocess.run(command, input='', 
        stdout=subprocess.PIPE, shell=True, universal_newlines=True)
      if compProc.returncode != 0:
        raise PykeError(f'<!error>Error<!/>: command failed with return value ${compProc.returncode}')
      t.print('Command completed <!success>successfully<!/>.')
      return compProc
    finally:
      timer.done()


    
