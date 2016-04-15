import math
from PySide import QtCore, QtGui, QtOpenGL
from FabricEngine import Core
from FabricEngine.FabricUI import *  
from SHContextualMenu import SHContextualMenu

class SHViewport(Viewports.ViewportWidget):
  sceneChanged = QtCore.Signal()
  viewportDestroying = QtCore.Signal()
  addCommands = QtCore.Signal()
  manipsAcceptedEvent = QtCore.Signal(bool)

  def __init__(self, renderer, scene, index, orthographic, context, parent, sharedWidget):
    # Need to hold the context
    self.orthographic = orthographic
    self.shGLScene = scene
    self.qglContext = context
    self.samples = self.qglContext.format().samples()
    self.viewportIndex = index
    self.viewport = None
    self.orthographic = False
    self.alwaysRefresh = False
    self.shGLRenderer = renderer

    client = renderer.getClient()
    super(SHViewport, self).__init__(client, QtGui.QColor(), self.qglContext, parent, sharedWidget, parent.settings)

    # Force to track mouse movment when not clicking
    self.setMouseTracking(True)
    self.setAcceptDrops(True)
    self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    self.viewport = self.shGLRenderer.getOrAddViewport(self.viewportIndex)

  def detachFromRTRViewport(self):
    if(self.viewportIndex > -1): self.shGLRenderer.removeViewport(self.viewportIndex)
    self.viewportIndex = -1
  
  def closeEvent(self): 
    detachFromRTRViewport()
    self.viewportDestroying.emit(self.viewportIndex)
   
  def setOrthographic(self, orthographic): 
    self.orthographic = orthographic
    self.shGLRenderer.setOrthographicViewport(self.viewportIndex, self.orthographic)
  
  def paintGL(self):
    self.computeFPS()
    self.shGLRenderer.render(self.viewportIndex, self.width, self.height, self.samples)
    if(self.alwaysRefresh): self.update()
  
  def resizeGL(self, width, height): 
    self.width = width
    self.height = height
  
  def toggleAlwaysRefresh(self):
    if self.alwaysRefresh:self.alwaysRefresh = False
    else: self.alwaysRefresh = True

  def isOrthographic(self):
    return self.orthographic

  def getViewportIndex(self):
    return self.viewportIndex
 
  def alwaysRefreshes(self):
    return self.alwaysRefresh

  def getCamera(self): 
    return self.shGLRenderer.getCamera(self.viewportIndex)

  def enterEvent(self, event): 
    self.grabKeyboard()

  def leaveEvent(self, event): 
    self.releaseKeyboard()

  def keyPressEvent(self, event):
    self.__onEvent(event)

  def keyReleaseEvent(self, event):
    self.__onEvent(event)

  def wheelEvent(self, event):
    self.__onEvent(event)

  def mouseMoveEvent(self, event):
    self.__onEvent(event)

  def mouseReleaseEvent(self, event):
    self.__onEvent(event)
    self.addCommands.emit()
    
  def mousePressEvent(self, event):
    if self.shGLScene.hasSG():
      if not self.__onEvent(event) and event.button() == QtCore.Qt.RightButton:
        menu = SHContextualMenu(self.shGLScene)
        menu.exec_(self.mapToGlobal(event.pos()))
        self.sceneChanged.emit()
    
  def __onEvent(self, event):
    redrawAllViewports = False
    if self.shGLRenderer.onEvent(self.viewportIndex, event, redrawAllViewports, False):
      self.manipsAcceptedEvent.emit(redrawAllViewports)
      return True
    return False
  
  def dragEnterEvent(self, event):
    if event.mimeData().hasUrls() and (event.possibleActions() & QtCore.Qt.CopyAction):
      event.setDropAction(QtCore.Qt.CopyAction)
      event.accept()

  def dragMoveEvent(self, event): 
    if(event.mimeData().hasUrls() and (event.possibleActions() & QtCore.Qt.CopyAction)):
      # Convert to a mouseMove event
      mouseEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, event.pos(), QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
      redrawAllViewports = False
      if self.shGLRenderer.onEvent(self.viewportIndex, mouseEvent, redrawAllViewports, True):
        self.manipsAcceptedEvent.emit(redrawAllViewports)

  def dropEvent(self, event):
    if self.shGLScene.hasSG(): 
      myData = event.mimeData()
      if myData is None: return
      if event.mimeData().hasUrls() == False: return

      pathList = []
      for url in event.mimeData().urls():
        pathList.append(url.toLocalFile())
      if len(pathList) == 0: return
       
      pos = self.shGLRenderer.get3DScenePosFrom2DScreenPos(self.viewportIndex, event.pos())
      pathList = Util.StringUtils.ProcessPathQStringForOsX(pathList)
      self.shGLScene.addExternalFileList(
        pathList, 
        event.keyboardModifiers() & QtCore.Qt.ControlModifier, 
        pos[0],
        pos[1],
        pos[2])
      event.acceptProposedAction()
      self.sceneChanged.emit()

  def onSceneUpdated(self, scene):
    self.shGLScene = scene
