import os
import sys
import importlib
from ansiTerm.ansiTerm import ansiTerm as t
from pyke.PykeError import PykeError
from pyke.terminal import terminal
from pyke.timer import timer
from pyke.FileFinder import FileFinder
from pyke.ObjectData import ObjectData, Usage
import pyke.FileFinder


def setTerminalStyles():
  t.setStyle('initial', {
    'bg-color': 'gs-0',
    'fg-color': 'system-dk-white',
    'bold': 'off'
  })

  t.setStyle('pathDir', {
    'fg-color': 'system-dk-cyan'
  })

  t.setStyle('pathBasename', {
    'fg-color': 'system-lt-cyan'
  })

  t.setStyle('shellCommand', {
    'fg-color': 'system-lt-black'
  })

  t.setStyle('usage', {
    'fg-color': 'system-dk-yellow'
  })

  t.setStyle('command', {
    'fg-color': 'system-lt-blue'
  })

  t.setStyle('project', {
    'fg-color': 'system-lt-yellow'
  })

  t.setStyle('warning', {
    'fg-color': 'system-lt-yellow'
  })

  t.setStyle('error', {
    'fg-color': 'system-lt-red'
  })

  t.setStyle('timerReportDark', {
    'fg-color': 'system-dk-magenta'
  })

  t.setStyle('timerReportLight', {
    'fg-color': 'system-lt-magenta'
  })


def printUsage():
  print ('Usage: RTFM')


def makeNewProject(path, data):
  peeDirs = []
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
  setTerminalStyles()
  print (t.pushState('initial'))

  timer.start("pyke")

  try:
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
          t.print(f'<!error>Error:<!/> {e}')
          shouldPrintUsage = True
          break

    if shouldPrintUsage:
      printUsage()

  finally:
    timer.done()
    timer.report(data.get('verbosity', "terse") == "verbose")
    print (t.popStates())

    #print (data)
    #print (os.environ)
