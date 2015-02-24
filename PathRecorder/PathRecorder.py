import os,datetime
import unittest
import numpy as np
from __main__ import vtk, qt, ctk, slicer

#
# PathRecorder
#

class PathRecorder:
  def __init__(self, parent):
    parent.title = "Path Recorder" # TODO make this more human readable by adding spaces
    parent.categories = ["IGT"]
    parent.dependencies = []
    parent.contributors = ["Alireza Mehrtash (BWH)"] 
    parent.helpText = """ This module is for recording and displaying the position of tracking devices connected through OpenIGTLink.
    """
    parent.acknowledgementText = """
    
""" # replace with organization, grant and thanks.
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['PathRecorder'] = self.runTest

  def runTest(self):
    tester = PathRecorderTest()
    tester.runTest()

#
# qPathRecorderWidget
#

class PathRecorderWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    self.transformNode = None
    self.transformNodeObserverTag = None
    self.transformObserverTag= None    
    self.transform = None
    self.acquireButtonFlag = False
    self.collectSignal = False
    self.pointerPosition = np.zeros(3)
    self.pointsCounts = 0
    self.recordedpoint = np.zeros(3)
    
    self.statusTimer = qt.QTimer()
    self.statusTimer.setInterval(100)
    self.statusTimer.connect('timeout()', self.changeTrackerStatus)
   
    if not parent:
      self.setup()
      self.parent.show()
  
  
  def setup(self):
    
    self.PathRecorderModuleDirectoryPath = slicer.modules.pathrecorder.path.replace("PathRecorder.py","")
    # Instantiate and connect widgets ...

    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "PathRecorder Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)
    
    # 
    # Input fiducial node selector
    #
    self.inputFiducialsNodeSelector = slicer.qMRMLNodeComboBox()
    self.inputFiducialsNodeSelector.nodeTypes = ['vtkMRMLMarkupsFiducialNode']
    self.inputFiducialsNodeSelector.selectNodeUponCreation = True
    self.inputFiducialsNodeSelector.addEnabled = True
    self.inputFiducialsNodeSelector.removeEnabled = False 
    self.inputFiducialsNodeSelector.noneEnabled = True
    self.inputFiducialsNodeSelector.showHidden = False
    self.inputFiducialsNodeSelector.showChildNodeTypes = False
    self.inputFiducialsNodeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputFiducialsNodeSelector.objectName = 'inputFiducialsNodeSelector'
    self.inputFiducialsNodeSelector.toolTip = "Select storage node for the recorded points (Markup-Fiducial-Node)."
    #inputFiducialsNodeSelector.connect('currentNodeChanged(bool)', self.enableOrDisableCreateButton)
    parametersFormLayout.addRow("Storage Node:", self.inputFiducialsNodeSelector)
    #self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', inputFiducialsNodeSelector, 'setMRMLScene(vtkMRMLScene*)')

    # Input Tracker node selector
    #
    self.inputTrackerNodeSelector = slicer.qMRMLNodeComboBox()
    self.inputTrackerNodeSelector.nodeTypes = ['vtkMRMLLinearTransformNode']
    self.inputTrackerNodeSelector.selectNodeUponCreation = True
    self.inputTrackerNodeSelector.addEnabled = False
    self.inputTrackerNodeSelector.removeEnabled = False
    self.inputTrackerNodeSelector.noneEnabled = True
    self.inputTrackerNodeSelector.showHidden = False
    self.inputTrackerNodeSelector.showChildNodeTypes = False
    self.inputTrackerNodeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputTrackerNodeSelector.objectName = 'inputTrackerNodeSelector'
    self.inputTrackerNodeSelector.toolTip = "Select the tracker linear transform node."
    #inputTrackerNodeSelector.connect('currentNodeChanged(bool)', self.enableOrDisableCreateButton)
    parametersFormLayout.addRow("Tracker Transform:", self.inputTrackerNodeSelector)
    #self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)', inputTrackerNodeSelector, 'setMRMLScene(vtkMRMLScene*)')
        
    
    #
    # Status Area
    #
    statusCollapsibleButton = ctk.ctkCollapsibleButton()
    statusCollapsibleButton.text = "Tracker Status"
    self.layout.addWidget(statusCollapsibleButton)

    # Layout within the status collapsible button
    statusFormLayout = qt.QFormLayout(statusCollapsibleButton)
    
    #
    # Status Button
    #
    self.statusRedIcon = qt.QIcon(self.PathRecorderModuleDirectoryPath+'/Resources/Icons/icon_DotRed.png')
    self.statusGreenIcon = qt.QIcon(self.PathRecorderModuleDirectoryPath+'/Resources/Icons/icon_DotGreen.png')
    
    self.statusButton = qt.QPushButton("")
    #self.statusButton.toolTip = "Tracker Status"
    self.statusButton.enabled = False
    self.statusButton.setIcon(self.statusRedIcon)
    self.statusButton.setMaximumWidth(25)
    
    # Bold and large font for needle label
    largeFont = qt.QFont()
    largeFont.setPixelSize(14)
    
    #
    # Label for showing the tracker position
    #
    self.currentCoordinatesLabel = qt.QLabel('[ NaN , NaN , NaN ]')
    self.currentCoordinatesLabel.setToolTip("Tracker Position")
    statusFormLayout.addRow(self.statusButton,self.currentCoordinatesLabel)
    
    #
    # Collect Area
    #
    collectCollapsibleButton = ctk.ctkCollapsibleButton()
    collectCollapsibleButton.text = "Acquire Points"
    self.layout.addWidget(collectCollapsibleButton)

    # Layout within the collect collapsible button
    collectFormLayout = qt.QFormLayout(collectCollapsibleButton)
    
    #
    # Name base line-edit
    # 
    self.nameBaseLineEdit = qt.QLineEdit()
    self.nameBaseLineEdit.setToolTip("Fiducials Name Base")
    collectFormLayout.addRow("Fiducials Name Base:",self.nameBaseLineEdit)
    
    #
    # Single Acquire Button
    #
    self.singleAcquireButton = qt.QPushButton("Single Point")
    self.singleAcquireButton.toolTip = "Acquire a single point at the current position."
    self.singleAcquireButton.enabled = True
    collectFormLayout.addRow(self.singleAcquireButton)  
        
    #
    # Continuous Acquire Button
    #
    self.recordButtonIcon = qt.QIcon(self.PathRecorderModuleDirectoryPath+'/Resources/Icons/icon_Record.png')
    self.stopButtonIcon = qt.QIcon(self.PathRecorderModuleDirectoryPath+'/Resources/Icons/icon_Stop.png')
    self.acquireButton = qt.QPushButton("Continuous")
    self.acquireButton.toolTip = "Start acquiring points continiously."
    self.acquireButton.enabled = True
    self.acquireButton.checkable = True
    self.acquireButton.setIcon(self.recordButtonIcon);
    #self.acquireButton.setMinimumWidth(80)
    #self.acquireButton.setMaximumWidth(80)
    collectFormLayout.addRow(self.acquireButton)
      
    #
    # Distance-based Radio Button
    #
    self.distanceBasedButton = qt.QRadioButton("Minimum Distance:")
    self.distanceBasedButton.setChecked(1)
    
    #collectFormLayout.addRow()
    
    # Distance slider
    distanceSlider = ctk.ctkSliderWidget()
    #distanceSlider.decimals = 0
    distanceSlider.minimum = 0.1
    distanceSlider.maximum = 100
    distanceSlider.suffix = " mm"
    distanceSlider.value = 1
    distanceSlider.toolTip = "Set minimum distance between recorded points"
    self.distanceSlider = distanceSlider
    collectFormLayout.addRow("Minimum Distance:", distanceSlider)

    #
    # Delete Button
    #
    self.deleteButton = qt.QPushButton("Delete")
    self.deleteButton.toolTip = "Delete all the points."
    self.deleteButton.enabled = True
    collectFormLayout.addRow(self.deleteButton)

    #
    # Export Area
    #
    exportCollapsibleButton = ctk.ctkCollapsibleButton()
    exportCollapsibleButton.text = "Export Points"
    self.layout.addWidget(exportCollapsibleButton)

    # Layout within the dummy collapsible button
    exportFormLayout = qt.QFormLayout(exportCollapsibleButton)
        
    #
    # Load Button
    #
    self.exportDirectoryButton = ctk.ctkDirectoryButton()
    exportFormLayout.addRow(self.exportDirectoryButton)

    #
    # Name base line-edit
    # 
    self.fileNameBaseLineEdit = qt.QLineEdit()
    self.fileNameBaseLineEdit.setToolTip("File name base")
    self.fileNameBaseLineEdit.text = 'PathRecorder'
    exportFormLayout.addRow("File Name Base:",self.fileNameBaseLineEdit)

    #
    # Save Button
    #
    saveButtonIcon = qt.QIcon(self.PathRecorderModuleDirectoryPath+'/Resources/Icons/icon_Save.png')
    self.exportButton = qt.QPushButton()
    self.exportButton.setIcon(saveButtonIcon)
    self.exportButton.toolTip = "Save points."
    self.exportButton.enabled = True
    exportFormLayout.addRow(self.exportButton)
    
    # connections
    self.inputFiducialsNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.setAnnotationHierarchyNode)
    self.inputTrackerNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.setTransformNode)
    self.distanceBasedButton.connect('toggled(bool)', self.distanceBasedSelected)
    self.acquireButton.connect('toggled(bool)', self.onAcquireButtonToggled)
    self.singleAcquireButton.connect('clicked()', self.onSingleAcButtonClicked)
    self.deleteButton.connect('clicked()', self.onDeleteButtonClicked)
    self.exportButton.connect('clicked()', self.onExportButtonClicked)
    #self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    #self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

  def setTransformNode(self, newTransformNode):
    """Allow to set the current Transform node. 
    Connected to signal 'currentNodeChanged()' emitted by Transform node selector."""
    
    #  Remove previous observer
    if self.transformNode and self.transformNodeObserverTag:
      self.transformNode.RemoveObserver(self.transformNodeObserverTag)
    if self.transform and self.transformObserverTag:
      self.transform.RemoveObserver(self.transformObserverTag)
    
    newTransform = None
    if newTransformNode:
      # newTransform = newTransformNode.GetMatrixTransformToParent()
      newTransform = vtk.vtkMatrix4x4()
      newTransformNode.GetMatrixTransformToWorld(newTransform)
      # Add TransformNode ModifiedEvent observer
      self.TransformNodeObserverTag = newTransformNode.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent , self.onTransformNodeModified)
      # Add Transform ModifiedEvent observer
      self.transformObserverTag = newTransform.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.onTransformNodeModified)
      self.transformObserverTag = newTransform.AddObserver('TransformModifiedEvent', self.onTransformModified)
      
    self.transformNode = newTransformNode
    self.transform = newTransform
    
    # Update UI
    self.updateWidgetFromMRML()
  
  def setAnnotationHierarchyNode(self, newAnnotationHeirarchyNode):  
    # Update UI
    self.activeMarkupsNode = newAnnotationHeirarchyNode
    self.pointsCounts = 0
    # markup-change
    #self.pointsCounts =  newAnnotationHeirarchyNode.GetNumberOfChildrenNodes()
    # Select the newAnnotationHeirarchyNode as the active Annotation Hierarchy for storing points
    #newAnnotationHeirarchyNodeID = newAnnotationHeirarchyNode.GetID()
    #annotationsLogic = slicer.modules.annotations.logic()
    #annotationsLogic.SetActiveHierarchyNodeID(newAnnotationHeirarchyNodeID)
    markupsLogic = slicer.modules.markups.logic()
    markupsLogic.SetActiveListID(newAnnotationHeirarchyNode)
    
    
  def updateWidgetFromMRML(self):
    logic = PathRecorderLogic()
    if self.transform:
      
      oldPosition = self.recordedpoint
      self.pointerPosition = logic.readPointerTip(self.transformNode)
      pointerDisplacement = oldPosition - self.pointerPosition
      self.pointerDisplacementDistance = np.sqrt(np.mean(pointerDisplacement**2))
      newLabel = '[ ' + str("{0:.1f}".format(self.pointerPosition[0])) + ' , '+ str("{0:.1f}".format(self.pointerPosition[1]))+ ' , '+ str("{0:.1f}".format(self.pointerPosition[2])) + ' ]'
      self.statusButton.enabled = True
      self.statusButton.setIcon(self.statusGreenIcon)
      self.statusTimer.start()
      #self.acquireTimer.setInterval(self.timeSlider.value)
      #self.acquireTimer.start()
      self.timerCollectSignal = False
      
      self.currentCoordinatesLabel.setText(newLabel)
      
      self.collectSignal = self.pointerDisplacementDistance > self.distanceSlider.value
        
      if (self.acquireButtonFlag and self.collectSignal ):
        self.pointsCounts += 1
        logic.acquirePoints(self.activeMarkupsNode,self.pointerPosition,self.nameBase,self.pointsCounts)
        self.recordedpoint = self.pointerPosition
    
    if self.transformNode:
      pass
      
  def changeTrackerStatus(self):
    self.statusButton.setIcon(self.statusRedIcon)   
    
  def onTransformModified(self, observer, eventid):
    self.updateWidgetFromMRML()
    
  def onTransformNodeModified(self, observer, eventid):
    self.updateWidgetFromMRML()
 
  def onAcquireButtonToggled(self, checked):
    if checked:
      self.nameBase =  self.nameBaseLineEdit.text 
      self.acquireButton.text = "Stop"
      self.acquireButton.setIcon(self.stopButtonIcon);
      self.acquireButtonFlag = True
      
      self.distanceBasedButton.enabled = False
      
    else:
      self.acquireButton.text = "Continuous"
      self.acquireButtonFlag = False
      self.acquireButton.setIcon(self.recordButtonIcon);
      self.distanceBasedButton.enabled = True
  
  def onDeleteButtonClicked(self):
    fidNode = self.activeMarkupsNode
    print fidNode.GetNumberOfFiducials()
    fidNode.RemoveAllMarkups()
    print fidNode.GetNumberOfFiducials()
    self.pointsCounts = 0
  
  def onSingleAcButtonClicked(self):
    logic = PathRecorderLogic()
    self.nameBase =  self.nameBaseLineEdit.text
    self.pointsCounts += 1
    logic.acquirePoints(self.activeMarkupsNode, self.pointerPosition,self.nameBase,self.pointsCounts)
  
  def onExportButtonClicked(self):
    #print 'on Export...'
    timeStamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    print self.exportDirectoryButton.directory
    directory = self.exportDirectoryButton.directory
    fileName =  directory + '/' + self.fileNameBaseLineEdit.text +' (' + timeStamp+ ').txt'

    fidNode = self.activeMarkupsNode
    n = fidNode.GetNumberOfFiducials()
    print n
    if n == 0: 
      return
    p = np.zeros((n,3))
    for i in xrange(n):
      #f = collection.GetItemAsObject(i)
      coords = [0,0,0]
      fidNode.GetNthFiducialPosition(i,coords)
      #f.GetFiducialCoordinates(coords)
      p[i] = coords
    np.set_printoptions(precision=2)
    # numpy.savetxt(fname, X, fmt='%.18e', delimiter=' ', newline='\n', header='', footer='', comments='# ')
    print fileName
    np.savetxt(fileName, p, fmt='%.2f')
  
  def distanceBasedSelected(self):
    self.distanceSlider.enabled = True
    #self.timeSlider.enabled = False
    #self.timeBased = False

  def cleanup(self):
    pass

  def onSelect(self):
    self.acquireButton.enabled = self.inputSelector.currentNode() and self.outputSelector.currentNode()


  def onReload(self,moduleName="PathRecorder"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer

    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)

    # delete the old widget instance
    if hasattr(globals()['slicer'].modules, widgetName):
      getattr(globals()['slicer'].modules, widgetName).cleanup()

    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()
    setattr(globals()['slicer'].modules, widgetName, globals()[widgetName.lower()])

  def onReloadAndTest(self,moduleName="PathRecorder"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(), 
          "Reload and Test", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")

#
# PathRecorderLogic
#

class PathRecorderLogic:
  """This class should implement all the actual 
  computation done by your module.  The interface 
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    pass

  def hasImageData(self,volumeNode):
    """This is a dummy logic method that 
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      print('no volume node')
      return False
    if volumeNode.GetImageData() == None:
      print('no image data')
      return False
    return True
  
  def readPointerTip(self, transformNode):
    transform = vtk.vtkMatrix4x4()
    transformNode.GetMatrixTransformToWorld(transform)
    x = transform.GetElement(0,3)
    y = transform.GetElement(1,3)
    z = transform.GetElement(2,3)
    position = np.array([x,y,z])
    return position
  
  def acquirePoints(self,activeMarkupsNode,pointerPosition,nameBase,pointCounts):     
      
      fidNode = activeMarkupsNode
      fidNode.LockedOn()
      n = fidNode.AddFiducial(pointerPosition[0],pointerPosition[1],pointerPosition[2])
      fidLabel = nameBase + " "+ str(pointCounts)
      fidNode.SetNthFiducialLabel(n, fidLabel)
      fidNode.SetNthMarkupLocked(n,1)
      
  
  def run(self,inputVolume,outputVolume):
    """
    Run the actual algorithm
    """
    return True

class PathRecorderTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_PathRecorder1()

  def test_PathRecorder1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    # import urllib
    # downloads = (
        # ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        # )

    # for url,name,loader in downloads:
      # filePath = slicer.app.temporaryPath + '/' + name
      # if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        # print('Requesting download %s from %s...\n' % (name, url))
        # urllib.urlretrieve(url, filePath)
      # if loader:
        # print('Loading %s...\n' % (name,))
        # loader(filePath)
    # self.delayDisplay('Finished with download and loading\n')

    # volumeNode = slicer.util.getNode(pattern="FA")
    # logic = PathRecorderLogic()
    # self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
