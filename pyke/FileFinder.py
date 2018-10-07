import os
import json

class FileFinder:
  searchDirsAdded = set()
  searchDirs = []
  foundPaths = {}
  

  @staticmethod
  def includeSearchDirectory(direc):
    if direc not in FileFinder.searchDirsAdded:
      FileFinder.searchDirs.append(direc)
      FileFinder.searchDirsAdded.add(direc)
  

  def __init__(self):
    pass
  

  def __str__(self):
    s = (f'FileFinder searchDirs:')
    for d in FileFinder.searchDirs:
      s += f'\n  {d}'
    return s


  def find(self, filename, verbosity):
    lookDir = os.path.abspath(os.getcwd())
    lastDir = ''
    path = ''

    while lastDir != '/':
      path = os.path.join(lookDir, filename)
      if os.path.exists(path):
        if verbosity == 'debug':
          print (f'  Found {path}')
        yield path
      lastDir = lookDir
      if lookDir != '/':
        lookDir = os.path.abspath(os.path.join(lookDir, '..'))

    for lookDir in FileFinder.searchDirs:
      path = os.path.join(lookDir, filename)
      if os.path.exists(path):
        if verbosity == 'debug':
          print (f'  Found {path}')
        yield path
