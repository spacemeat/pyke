import json
from .PykeError import PykeError
from .FileFinder import FileFinder
from .terminal import terminal as t
from .timer import timer

import pdb

KEY_groupDefaults = "usageGroupDefaults"

class Usage:
  def __init__(self, subTree, groups, aliases):
    self.subTree = subTree
    self.groups = groups
    self.aliases = aliases


class Command:
  def __init__(self, subTree, aliases):
    self.subTree = subTree
    self.aliases = aliases


class ObjectData:
  def __init__(self, data = {}):
    self.data = data
    self.usages = {}
    self.usagesUsed = set()
    self.commands = {}
    self.merge(data)
    self.groupsSelected = set()
    self.pykeFilePath = ''
  

  def __str__(self):
    return json.dumps(self.data, indent=4)

  
  def get(self, key, defv = None):
    return self.data.get(key, defv)
  

  def setValue(self, key, value):
    # TODO: Values are strings. Deal with different types.
    # TODO: Check operations, etc
    self.data[key] = value
  
  
  def use(self, usage, finder = None):
    def useJson(jsonData):
      # Resolve pykeExtDirs relative paths with json file location. Later they will merge in place.
      fixedDirs = []
      for extDir in jsonData.get("pykeExtDirs", []):
        if not os.path.isabs(extDir):
          extDir = os.path.join(os.path.dirname(path), extDir)
        fixedDirs.append(extDir)
      jsonData["pykeExtDirs"] = fixedDirs

      # 'Inherit' all usages in the 'is' value. If
      # we are a usage inheriting itself, then find
      # the same usage ID further down the search 
      # path using the same directory generator.
      for whatUsageIs in jsonData.get("is", []):
        if whatUsageIs.startswith(':'):
          _, *groups = whatUsageIs.split(':')
          groups = [g for g in groups if g != '']
          if len(groups) > 0:
            for group in groups:
              self.resolveGroupDefault(group)
          else:
            self.resolveAllGroupDefaults()
        else:
          if self.data.get('verbosity') == 'debug':
            print (f'{usage} is: {whatUsageIs}')
          if whatUsageIs == usage:
            self.use(whatUsageIs, finder)
          else:
            self.use(whatUsageIs)

      # Now merge this data in. New usages will be 
      # registered, new search paths added.
      self.merge(jsonData)

      # Now use any automatically used usages. Usages.
      for whatUsageUses in jsonData.get("use", []):
        self.use(whatUsageUses)

    if usage == '':
      timer.start('Usage: pyke.json')
    else:
      timer.start(f'Usage: {usage}')
    try:
      if usage in self.usagesUsed:
        if self.data.get('verbosity') == 'debug':
          print (f'Already used --{usage}.')
      else:
        if self.data.get('verbosity') == 'debug':
          print (f'Using "{usage}"')
        if usage not in self.usages:
          if usage == '':
            filename = 'pyke.json'
          else:
            filename = f'{usage}.pyke.json'
          if finder == None:
            finder = FileFinder()
          for path in finder.find(filename, self.data.get('verbosity')):
            jsonData = {}
            with open(path) as f:
              jsonData = json.loads(f.read())
            useJson(jsonData)

            if usage == '':
              self.pykeFilePath = path
            # Only use the first one we encounter; if we
            # are overriding one from up the tree, we have
            # to specify it in the 'is' value (handled
            # above).
            break
        else:
          jsonData = self.usages[usage].subTree
          useJson(jsonData)

        if usage in self.usages:
          for al in self.usages[usage].aliases:
            self.usagesUsed.add(al)


      # If this usage belongs to a group, mark that group
      # as having been used.
      # Note: self.usages may be changed by useJson() above
      if usage in self.usages:
        self.merge(self.usages[usage].subTree)
        for group in self.usages[usage].groups:
          self.groupsSelected.add(group)

    finally:
      timer.done()


  def merge(self, operand):
    def copyTree(node):
      if isinstance(node, list):
        ret = []
        for e in node:
          ret.append(copyTree(e))
      elif isinstance(node, dict):
        ret = {}
        for k, v in node.items():
          ret[k] = copyTree(v)
      else:
        ret = node
      return ret

    def mergeTree(op, desNode, srcNode):
      if isinstance(srcNode, list):
        ret = [*desNode]
        if op == '+':
          for elem in srcNode:
            elem = elem.strip()
            # print ('src list element {}'.format(elem))
            if elem not in ret:
              ret.append(copyTree(elem))
        elif op == '-':
          for elem in srcNode:
            elem = elem.strip()
            if elem in ret:
              ret.remove(elem)
          
        # print (' - final list: {}'.format(ret))
        return ret

      elif isinstance(srcNode, dict):
        if isinstance(desNode, dict):
          ret = {**desNode}
        else:
          ret = {}
        for sk, sv in srcNode.items():
          # remove all whitespace
          sk = ''.join(sk.split())
          op = '='
          if sk[0] == '+':
            op = '+'
            sk = sk[1:].lstrip()
          elif sk[0] == '-':
            if sk[1] != '-':  # -- is not an operation; ignore it
              op = '-'
              sk = sk[1:].lstrip()

          if sk in desNode:
            # print ('merging src dict element {}'.format(sk))
            if op == '+':
              ret[sk] = mergeTree(op, ret[sk], sv)
            else:
              ret[sk] = copyTree(sv)
          else:
            # print ('adding src dict element {}'.format(sk))
            if op != '-':
              ret[sk] = copyTree(sv)
        return ret

      elif isinstance(desNode, list) or isinstance(desNode, dict):
        raise PykeError('Collection type mismatch: src is not a list or dict, but should be')
      
      else:
        # print ('src leaf element {}'.format(srcNode))
        return srcNode
      
      return desNode

    if isinstance(operand, ObjectData):
      operand = operand.data

    des = copyTree(self.data)
    self.data = mergeTree('+', des, operand)

    # gather any new usages
    for k, v in self.data.items():
      if k.startswith('--'):
        k = k[2:]
        groups = []
        aliases = []
        if ':' in k:
          k, *groups = [th.strip() for th in k.split(':')]
        if '|' in k:
          aliases = [al.strip() for al in k.split('|')]
        if len(aliases) == 0:
          aliases.append(k)
        
        for al in aliases:
          if al in self.usages:
            for g in groups:
              if g not in self.usages[al].groups:
                self.usages[al].groups.add(g)
          else:
            usage = Usage(v, set(*groups), aliases)
            self.usages[al] = usage

      elif k.startswith('!'):
        k = k[1:]
        aliases = []
        if '|' in k:
          aliases = [al.strip() for al in k.split('|')]
        if len(aliases) == 0:
          aliases.append(k)
        for al in aliases:
          if al in self.commands:
            for ali in aliases:
              if al not in self.commands[ali].aliases:
                self.commands[ali].aliases.append(al)
          else:
            self.commands[al] = (Command(v, aliases))


    # gather any new include search directories
    searchDirs = self.data.get('pykeFileSearchDirs', [])
    for direc in searchDirs:
      self.finder.includeSearchDirectory(direc)


  def resolveAllGroupDefaults(self):
    """ data[KEY_groupDefaults] = 
          "c++Std:c++14"
           ------         group name
                  -----   usage
    """
    for e in self.data.get(KEY_groupDefaults, []):
      if ':' in e:
        group, usageName = e.split(':', 1)
        if group not in self.groupsSelected:
          if self.data.get('verbosity') == 'debug':
            print (f'Resolving group default usages for "{group}"')
          self.groupsSelected.add(group)
          self.use(usageName)


  def resolveGroupDefault(self, group):
    if group in self.groupsSelected:
      return

    for e in self.data.get(KEY_groupDefaults, []):
      if ':' in e:
        groupName, usageName = e.split(':', 1)
        if groupName == group:
          if self.data.get('verbosity') == 'debug':
            print (f'Resolving group default usages for "{group}"')
          self.groupsSelected.add(group)
          self.use(usageName)
