import os
from pyke.timer import timer
from ..PykeError import PykeError
from .CPlusPlusTool import CPlusPlusTool


class Source:
  def __init__(self, dataEntry, srcPath, objFilePath):
    self.dataEntry = dataEntry

    self.srcPath = srcPath
    # self.srcExists = os.path.exists(self.srcPath)
    # self.srcMtime = os.path.getmtime(self.srcPath) if self.srcExists else 0

    self.objFilePath = objFilePath
    #self.objFileExists = os.path.exists(self.objFilePath)
    #self.objFileMtime = os.path.getmtime(self.objFilePath) if self.objFileExists else 0

    self.isIncludesResolved = False
    self.includedFiles = []

  def isUpToDate(self, targetMtime):
    for inc in self.includedFiles:
      if os.path.getmtime(inc) > targetMtime:
        return False
    if self.srcMtime > targetMtime:
      return False
    return True


class CPlusPlusLinuxGnuTool(CPlusPlusTool):
  def __init__(self, project):
    super().__init__(project)
    self.data = project.data
    self.path = project.path
    self.sources = []

    srcDir = self.data.get('sourceDir', '')
    objFileExtension = self.data.get('objFileExtension', 'o')
    for srcEntry in self.data.get('source', []):
      srcPath = os.path.normpath(
        os.path.join(self.path, srcDir, srcEntry))
      objFilePath, _ = srcPath.splitext(srcPath)
      objFilePath = ''.join([objFilePath, '.', objFileExtension])
      self.sources.append(Source(srcEntry, srcPath, objFilePath))
      
    self._prepareProjectData()


  def _prepareProjectData(self):
    self._makeProjectDir()
    self._makeIncludeDirsArg()
    self._makeLibDirsArg()
    self._makeLibsArg()
    self._makeObjFilePathsArg()
    self._makePackageIncludes()
    self._makePackageLibs()
    

  def _ensureDirExists(self, dirname):
    try:
      if not os.path.exists(dirname):
        os.makedirs(dirname)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise


  def _makeProjectDir(self):
    projectDir = self.data.get('projectDir', '.')
    # TODO: test ~/paths
    if not os.path.isabs(projectDir):
      projectDir = os.path.normpath(
        os.path.join(self.path, projectDir))
      self.data.data['projectDir'] = projectDir


  def _makeIncludeDirsArg(self):
    includeDirsArg = [f'-I{os.path.join(self.path, path)}' 
      for path in self.data.get('includeDirs')]
    self.data.data['includeDirsArg'] = includeDirsArg


  def _makeLibDirsArg(self):
    # making a unique, ordered set
    dirs = set()
    libDirs = []
    
    # TODO: Fix up once dependency projects are a thing
    # TODO: Also make it recursive
    for _, p in enumerate(self.project.dependencyProjects):
      d = os.path.dirname(p.tool.get_output_path())
      if d not in dirs:
        dirs.add(d)
        libDirs.append(d)
        
    for d in self.data.get('libDirs', []):
      d = os.path.join(self.path, d)
      if d not in dirs:
        dirs.add(d)
        libDirs.append(d)
        
    libDirs = [f'-L{d}' for d in libDirs]
    self.data.data['includeDirsArg'] = ' '.join(libDirs)


  def _makeLibsArg(self):
    libs = [f'-l{path}' 
      for path in self.data.get('libs', [])]
    self.data.data['libsArg'] = ' '.join(libs)


  def _makeObjFilePathsArg(self):
    if self.data.get('wholeProgram'):
      self.data.data['objFilePathsArg'] = self.data.get('compileOutputName', f'{self.data.get("name")}.o')
    else:
      objs = [src.objFilePath for src in self.sources]
      self.data.data['objFilePathsArg'] = ' '.join(objs)


  def _makePackageIncludes(self):
    packages = self.data.get('packages', [])
    if len(packages) > 0:
      self.data.data['packagesIncludesArg'] = f'`pkg-config --cflags {" ".join(packages)}`'
    else:
      self.data.data['packagesIncludesArg'] = ''
  

  def _makePackageLibs(self):
    packages = self.data.get('packages', [])
    if len(packages) > 0:
      self.data.data['packagesLibsArg'] = f'`pkg-config --libs {" ".join(packages)}`'
    else:
      self.data.data['packagesLibsArg'] = ''
  

  def _resolveIncludes(self, srcIdx):
    src = self.srouces[srcIdx]
    self.data.data['srcPath'] = src.srcPath
    cppCmds = self.data.get('resolveIncludesCmds', [])
    for cppCmd in cppCmds:
      try:
        compProc = self._doShellCommand(cmpCmd)
      except PykeError as e:
        src.isIncludesResolved = False
        raise PykeError(f'<!error>Error<!/> resolving #includes for ${t.makePath(src.srcPath)}:\n${e}')

      src.isIncludesResolved = True
      # each line of input can have n paths
      src.includedFiles = [f 
        for d in compProc.stdout.splitlines() [1:]
        for f in str(d).rstrip(" \\").split()]


  def _validate_src(self, srcIdx):
    src = self.sources[srcIdx]
    t.print (f'Validating ${t.makePath(src.srcEntry)}:')
    self._resolveIncludes(srcIdx)
    if src.isIncludesResolved:
      raise PykeError(f'${t.makePath(srcEntry)} has #include paths that cannot be resolved.')


  def cleanProject(self):
    pass


  def buildProject(self):
    outputType = self.data.get('outputType')
    if outputType == "lib":
      self._buildLib()
    elif outputType == "so":
      self._buildSo()
    elif outputType == "exe":
      self._buildExe()
    else:
      raise PykeError(f'Invalid outputType: {outputType}')


  def _buildLib(self):
    if self.data.get('wholeProgram', False):
      self._buildLibWholeProgram()
    else:
      self._buildLibFromObjects()


  def _buildLibWholeProgram(self):
    print (f'Building library with whole-program call.')
    outputDir = self.data.get('outputDir')
    self._ensureDirExists(outputDir)
    # Note: We use data.data[] here instead of data.get() because
    # we want the untranslated text.
    outputName = self.data.data['outputName']
    self.data.data['outputName'] = 'TODO' # TODO
    try:
      self._doShellCommandList(self.data.get('wholeBuildCmds', []))
    except PykeError as e:
      raise PykeError(f'<!error>Error<!/> building ${t.makePath(outputPath)}:\n${e}')


  def _buildLibFromObjects(self):
    print (f'Building library with per-source calls.')
    for idx in range(0, len(self.sources)):
      self._buildObject(idx)

    self._archiveObjects()

  
  def _buildSo(self):
    if self.data.get('wholeProgram', False):
      self._buildSoWholeProgram()
    else:
      self._buildSoFromObjects()


  def _buildSoWholeProgram(self):
    print (f'Building shared library with whole-program call.')
    pass


  def _buildSoFromObjects(self):
    print (f'Building shared library with per-source calls.')
    pass


  def _buildExe(self):
    if self.data.get('wholeProgram', False):
      self._buildExeWholeProgram()
    else:
      self._buildExeFromObjects()


  def _buildExeWholeProgram(self):
    print (f'Building executable with whole-program call.')


  def _buildExeFromObjects(self):
    print (f'Building executable with per-source calls.')
    for idx in range(0, len(self.sources)):
      self._buildObject(idx)
    self._linkObjects()


  def isUpToDate(self, targetMtime):
    outuptPath = self.data.get('outputPath')
    """
    if building from objects,
      foreach source:
        if outputPath older than source.obj, return false
    else,
      foreach source:
        if outputPath older than source, return false
        foreach source.include,
          if ourputPath older than source.include, return false


    """


    if os.path.getmtime(outuptPath) > targetMtime:
      return False
    return True


  def _buildObject(self, srcIdx):
    pass


  def _linkObjects(self):
    pass


  def _archiveObjects(self):
    pass


def makeTool(project):
  return CPlusPlusLinuxGnuTool(project)
