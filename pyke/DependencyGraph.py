import os
from ..PykeError import PykeError


class DependencyGraph:
  class Node:
    def __init__(self, dependentPath, dependencyNode, buildFn = None):
      self.path = dependentPath
      self.exists = os.path.exists(self.path)
      self.mtime = os.path.getmtime(self.path) if self.exists else 0
      self.buildFn = buildFn
      if dependencyNode != None:
        self.dependencies = [dependencyNode]


    def update(self):
      mtime = 0
      for dep in self.dependencies:
        nmt = dep.update()
        if nmt > mtime:
          mtime = nmt
      
      if mtime > self.mtime:
        if self.buildFn != None:
          self.buildFn()
        self.exists = os.path.exists(self.path)
        self.mtime = os.path.getmtime(self.path) if self.exists else 0

      return self.mtime


  def __init__(self):
    nodes = {}


  def add(self, dependentPath, dependencyPath):
    dependencyNode = self.nodes.get(dependencyPath, None)
    if dependencyPath == None:
      dependencyNode = Node(dependencyPath, None)
      self.nodes[dependencyPath] = dependencyNode

    if dependentPath not in self.nodes:
      self.nodes[dependentPath] = Node(dependentPath, dependencyNode)
    else:
      self.nodes[dependentPath].dependencies.append(dependencyNode)

  
  def update(self, path):
    pathNode = self.nodes.get(path)
    if pathNode == None:
      raise PykeError(f'Invalid path {path}')
    pathNode.update()
