import os
import json
from pyke.terminal import terminal as t
from pyke.timer import timer
import inspect

class Project:
  def __init__(self, path, data):
    self.dependencyProjects = []
    self.path = path
    self.data = data
    """
    self.commands = []
    for k in self.data.data:
      if k.startswith('!'):
        command = k[1:].strip()
        self.commands.append(command)
    """

  def doCommand(self, command):
    timer.start(f'Command: {command}')
    try:
      if self.data.get('verbosity') == 'debug':
        print (f'Starting command "{command}"')
      if self.doCommandOverride(command) == False:
        raise PykeError(f'No command "{t.make_command_name(command)}" was found.')
    finally:
      timer.done()


  def doCommandOverride(self, command):
    """This method should be overridden in derivative Project classes. Overrides should return a call to super().doCommandOverride(command) instead of returning False."""
    if command == 'describe':
      self.doDescribe()
      return True
    else:
      return False


  def doDescribe(self):
    verbosity = self.data.get('verbosity', 'terse')
    self.describeDocs(verbosity)
    self.describeUsages(verbosity)
    self.describeCommands(verbosity)


  def describeDocs(self, verbosity):
    if verbosity == 'silent':
      return

    print ("")
    if verbosity == 'verbose':
        print ('=' * 60)
    
    print ("Project {0}\nat {1}\nType: {2}\nVersion: {3}\n".format(
        t.make_project_name(self.data.get("name")),
        t.make_project_path(self.path),
        t.make_project_type(self.data.get("type")),
        self.data.get('version')))
    
    if 'doc' in self.data.data:
      print (self.data.data['doc'].get('short', '<no docs>'))
      if verbosity == 'verbose':
        print (self.data.data['doc'].get('long', '<no docs>'))
    print('')

  
  def describeCommands(self, verbosity):
    if verbosity == 'silent':
      return
    elif verbosity == 'terse':
      print ('Available commands:')
    elif verbosity == 'verbose':
      print ('Pass any number of these commands once usages are set. Each will be run in sequence:')
    
    commandsSeen = set()
    for commandName, command in self.data.commands.items():
      if commandName in commandsSeen:
        continue

      for co in command.aliases:
        commandsSeen.add(co)

      commandAliases = f'  {" | ".join([f"{al}" for al in command.aliases])}'

      subTree = command.subTree
      docTree = subTree.get('doc', {})
      if verbosity == 'terse':
        desc = docTree.get('short', '')
        if desc == '':
          desc = docTree.get('long', '<no desc>')
        print (f'  {t.make_command(commandAliases)}: {desc}')
      elif verbosity == 'verbose':
        desc = docTree.get('long', '')
        if desc == '':
          desc = docTree.get('short', '<no desc>')
        print (f'  {t.make_command(commandAliases)}: {desc}')
    print('')


  def describeUsages(self, verbosity):
    if verbosity == 'silent':
      return

    elif verbosity == 'verbose':
      print ('Pass any number of these usages with \'--\', like \'--debug\'. Each will be applied in sequence')

    print ('Available usages (used usages are *\'d):')

    usagesSeen = set()
    for name, usage in self.data.usages.items():
      if name in usagesSeen:
        continue

      for al in usage.aliases:
        usagesSeen.add(al)
      
      usageIsUsed = name in self.data.usagesUsed

      print (f'  {"* " if usageIsUsed else "  "}{" | ".join([f"--{al}" for al in usage.aliases])}')
    print('')


def makeProject(path, data):
  return Project(path, data)

