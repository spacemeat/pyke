import os
import sys
import importlib
from pyke.PykeError import PykeError
from pyke.terminal import terminal as t
from pyke.timer import task_timer as Timer
from pyke.FileFinder import FileFinder
from pyke.ObjectData import ObjectData, Usage
import pyke.FileFinder


def printUsage():
  print ('Usage: RTFM')


def makeNewProject(path, data):
  peeDirs = []
#  peeDir = os.path.join(os.path.dirname(__file__), "projects")
#  if peeDir not in sys.path:
#    peeDirs.append(peeDir)

  for peeDir in data.get('pykeExtDirs', []):
    if not os.path.isabs(peeDir):
      peeDir = os.path.join(os.path.dirname(path), peeDir)
    if peeDir not in sys.path:
      peeDirs.append(extDir)

  pykeEnvExtDirs = os.environ.get('PYKE_EXT_DIRS', '').split(os.pathsep)
  pykeEnvExtDirs = [d for d in pykeEnvExtDirs if d != '']
  for peeDir in pykeEnvExtDirs:
    if not os.path.isabs(peeDir):
      peeDir = os.path.join(os.path.dirname(path), peeDir)
    if peeDir not in sys.path:
      peeDirs.append(peeDir)

  sys.path.extend(peeDirs)
  #print (f'Using sys.path = {sys.path}')
  m = importlib.import_module(
    ''.join(['pyke.projects.', data.get("type"), '_pykeProject']))
  np = m.makeProject(path, data)

  return np


def main(args):
  timer = Timer("pyke")

  shouldPrintUsage = False

  # prime FileFinder's search list
  FileFinder.includeSearchDirectory(os.getcwd())

  pykeEnvDirs = [d for d in 
    os.environ.get('PYKE_DIRS', '').split(os.pathsep) 
    if d != '']
  for peDir in pykeEnvDirs:
    FileFinder.includeSearchDirectory(peDir)

  pykeBuiltInDir = os.path.abspath(
      os.path.join(os.path.dirname(__file__), 'pyke/builtIn'))
  FileFinder.includeSearchDirectory(pykeBuiltInDir)

  data = ObjectData()
  data.use('default')
  data.use('')

  project = None

  if data.get('verbosity') == 'debug':
    print (str(FileFinder()))

  # parse command line
  for statement in args:
    if '=' in statement:
      operands = statement.split('=')
      typ = operands[0]
      val = operands[1]
      data.setValue(typ, val)
    elif statement.startswith('--'):
      pykeFileJson = getPykeFileJson()
      usage = statement[2:]
      data.use(usage)
    elif statement.startswith(':'):
      _, *groups = statement.split(':')
      groups = [g for g in groups if g != '']
      if len(groups) > 0:
        for group in groups:
          data.resolveGroupDefault(group)
      else:
        data.resolveAllGroupDefaults()
    else:
      command = statement
      try:
        if project == None:
          project = makeNewProject(data.pykeFilePath, data)
        project.doCommand(command)
      except PykeError as e:
        print (f'{t.make_error("Error:")} {str(e)}')
        shouldPrintUsage = True
        break

  if shouldPrintUsage:
    printUsage()
  
  timer.done()
  timer.report()

  # print (str(data))

"""
if __name__ == '__main__':
    main(args)
"""