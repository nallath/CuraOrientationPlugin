from typing import List, cast

from UM.Extension import Extension
from UM.PluginRegistry import PluginRegistry
from UM.Scene.SceneNode import SceneNode
from UM.Scene.Selection import Selection
from UM.Scene.SceneNode import SceneNode
from UM.Operations.GroupedOperation import GroupedOperation


from UM.Math.Vector import Vector
from UM.Math.Matrix import Matrix
from UM.Math.Quaternion import Quaternion
from UM.Resources import Resources

from UM.Message import Message
from UM.Logger import Logger
from cura.CuraApplication import CuraApplication

from cura.CuraVersion import CuraVersion  # type: ignore
from UM.Version import Version

from .CalculateOrientationJob import CalculateOrientationJob
from .SetTransformMatrixOperation import SetTransformMatrixOperation

from UM.i18n import i18nCatalog

import os

import numpy
import trimesh


Resources.addSearchPath(
    os.path.join(os.path.abspath(os.path.dirname(__file__)))
)  # Plugin translation file import

i18n_catalog = i18nCatalog("OrientationPlugin")

if i18n_catalog.hasTranslationLoaded():
    Logger.log("i", "OrientationPlugin Plugin translation loaded!")
    
class OrientationPlugin(Extension):
    def __init__(self):
        super().__init__()
        
        self._extended_mode = False
        
        self.addMenuItem(i18n_catalog.i18n("Calculate fast optimal printing orientation"), self.doFastAutoOrientation)
        self.addMenuItem(i18n_catalog.i18n("Calculate extended optimal printing orientation"), self.doExtendedAutoOrientiation)
        self.addMenuItem("", lambda: None)
        # Issue with the trimesh release provided with Cura 4.X
        if Version(CuraVersion).getMajor() >= 5:
            self.addMenuItem(i18n_catalog.i18nc("@item:inmenu", "Rotate in the main direction (X)"), self.rotateMainDirection)
        self.addMenuItem(i18n_catalog.i18nc("@item:inmenu", "Rotate the side direction (X)"), self.rotateSideDirection)
        self.addMenuItem(" ", lambda: None)
        self.addMenuItem(i18n_catalog.i18nc("@item:inmenu", "Reinit Rotation"), self.resetRotation)
        self.addMenuItem("  ", lambda: None)
        self.addMenuItem(i18n_catalog.i18n("Modify Settings"), self.showPopup)
        
        self._message = Message(title=i18n_catalog.i18nc("@info:title", "Orientation Plugin"))
        self._message.hide()
        
        self._currently_loading_files = []  # type: List[str]
        self._check_node_queue = []  # type: List[SceneNode]
        CuraApplication.getInstance().getPreferences().addPreference("OrientationPlugin/do_auto_orientation", False)
        self._do_auto_orientation = CuraApplication.getInstance().getPreferences().getValue("OrientationPlugin/do_auto_orientation")
        
        
        # Should the volume beneath the overhangs be penalized?
        CuraApplication.getInstance().getPreferences().addPreference("OrientationPlugin/min_volume", True)

        self._popup = None

        CuraApplication.getInstance().fileLoaded.connect(self._onFileLoaded)
        CuraApplication.getInstance().fileCompleted.connect(self._onFileCompleted)
        CuraApplication.getInstance().getController().getScene().sceneChanged.connect(self._onSceneChanged)
        CuraApplication.getInstance().getPreferences().preferenceChanged.connect(self._onPreferencesChanged)

        # Use the qml_qt6 stuff for 5.0.0 and up
        if Version(CuraVersion).getMajor() >= 5:
            self._qml_folder = "qml_qt6"
        else:
            self._qml_folder = "qml_qt5"

    def _onPreferencesChanged(self, name: str) -> None:
        if name != "OrientationPlugin/do_auto_orientation":
            return
        self._do_auto_orientation = CuraApplication.getInstance().getPreferences().getValue("OrientationPlugin/do_auto_orientation")

    def _createPopup(self) -> None:
        # Create the plugin dialog component
        path = os.path.join(cast(str, PluginRegistry.getInstance().getPluginPath(self.getPluginId())), self._qml_folder,
                            "SettingsPopup.qml")
        self._popup = CuraApplication.getInstance().createQmlComponent(path)
        if self._popup is None:
            return

    def showPopup(self) -> None:
        if self._popup is None:
            self._createPopup()
            if self._popup is None:
                return
        self._popup.show()

    def _onFileLoaded(self, file_name):
        self._currently_loading_files.append(file_name)

    def _onFileCompleted(self, file_name):
        if file_name in self._currently_loading_files:
            self._currently_loading_files.remove(file_name)

    def _onSceneChanged(self, node):
        if not self._do_auto_orientation:
            return  # Nothing to do!

        if not node or not node.getMeshData():
            return

        # only check meshes that have just been loaded
        if node.getMeshData().getFileName() not in self._currently_loading_files:
            return

        # the scene may change multiple times while loading a mesh,
        # but we want to check the mesh only once
        if node not in self._check_node_queue:
            self._check_node_queue.append(node)
            CuraApplication.getInstance().callLater(self.checkQueuedNodes)

    def checkQueuedNodes(self):
        for node in self._check_node_queue:
            if self._message:
                self._message.hide()
            auto_orient_message = Message(i18n_catalog.i18nc("@info:status", "Auto-Calculating the optimal orientation because auto orientation is enabled"), 0,
                                    False, -1, title=i18n_catalog.i18nc("@title", "Auto-Orientation"))
            auto_orient_message.show()
            job = CalculateOrientationJob([node], extended_mode=True, message=auto_orient_message)
            job.finished.connect(self._onFinished)
            job.start()

        self._check_node_queue = []

    def _getSelectedNodes(self, force_single = False) -> List[SceneNode]:
        self._message.hide()
        _selection = Selection.getAllSelectedObjects()[:]
        if force_single:
            if len(_selection) == 1:
                return _selection[:]

            self._message.setText(i18n_catalog.i18nc("@info:status", "No object selected to orient. Please select one object and try again."))
            self._message._message_type = Message.MessageType.ERROR
        else:
            if len(_selection) >= 1:
                return _selection[:]

            self._message.setText(i18n_catalog.i18nc("@info:status", "No objects selected to orient. Please select one or more objects and try again."))
            self._message._message_type = Message.MessageType.ERROR
            
        self._message.show()
        return []

    def resetRotation(self) -> None:
        """Reset the orientation of the mesh(es) to their original orientation(s)"""

        Selection.applyOperation(SetTransformOperation, None, Quaternion(), None)
        
    def rotateMainDirection(self) -> None:
        nodes_list = self._getSelectedNodes()
        if not nodes_list:
            return

        op = GroupedOperation()
        for node in nodes_list:
            mesh_data = node.getMeshData()
            if not mesh_data:
                continue
            
            hull_polygon = node.callDecoration("_compute2DConvexHull")
            # test but not sure in witch case we have this situation ?
            if not hull_polygon or hull_polygon.getPoints is None:
                Logger.log("w", "Object {} cannot be calculated because it has no convex hull.".format(node.getName()))
                continue

            points=hull_polygon.getPoints()
            # Get the Rotation Matrix     
            # Logger.log('d', "Points : \n{}".format(points))                  
            transform, rectangle = trimesh.bounds.oriented_bounds_2D(points) 

            # Change Transfo data
            # Don't ask me Why just test and try not sure of the validity of oriented_bounds_2D by trimesh 
            t = Matrix()
            Vect = [transform[1][1],0,transform[0][1]]
            t.setColumn(0,Vect)
            Vect = [transform[1][0],0,transform[0][0]]
            t.setColumn(2,Vect)

            #local_transformation.setColumn(1,transform[1])
            local_transformation = Matrix()
            local_transformation.multiply(t)
            local_transformation.multiply(node.getLocalTransformation())  

            # Log for debugging and Analyse           
            # Logger.log('d', "Local_transformation     :\n{}".format(node.getLocalTransformation())) 
            # Logger.log('d', "TransformMatrixOperation :\n{}".format(local_transformation))   
            # node.setTransformation(local_transformation)            
            op.addOperation(SetTransformMatrixOperation(node, local_transformation))

        op.push()

    def rotateSideDirection(self) -> None:
        nodes_list = self._getSelectedNodes()
        if not nodes_list:
            return

        op = GroupedOperation()
        for node in nodes_list:
            mesh_data = node.getMeshData()
            if not mesh_data:
                continue
            
            hull_polygon = node.callDecoration("_compute2DConvexHull")
            # test but not sure in witch case we have this situation ?
            if not hull_polygon or hull_polygon.getPoints is None:
                Logger.log("w", "Object {} cannot be calculated because it has no convex hull.".format(node.getName()))
                continue
 
            points=hull_polygon.getPoints()

            # Init
            np = 0
            l_v = 0
            for point in points:
                # Logger.log('d', "p{} X : {} Y : {}".format(np,point[0],point[1]))
                if np>0 :                         
                    new_position = Vector(point[0], point[1], 0)
                    lg=new_position-first_pt
                    lght = lg.length()
                    if lght>l_v :
                        l_v = lght
                        s_lg=lg

                    first_pt=new_position
                else :
                    first_pt = Vector(point[0], point[1], 0)             
                np+=1
            
            # Last vector  to close the loop       
            lg=Vector(points[0][0], points[0][1], 0)-first_pt
            lght = lg.length()
            if lght>l_v :
                s_lg=lg
                # Logger.log('d', "s_lg on las point : {}".format(s_lg))
            
            vectX = (1, 0, 0)
            vectY = (0, 1, 0)
            anGl= self._angle_between(vectX,(s_lg.x, s_lg.y, 0))
            deganGl = anGl/numpy.pi*180
            
            # For debuging output the vector director and the Angle ( in radians and degree)
            # Logger.log('d', "s_lg   : {}".format(s_lg))
            # Logger.log('d', "Angle : {} Angle° : {}".format(anGl,deganGl)) 

            dv=self._dot_vector(vectY,(s_lg.x, s_lg.y, 0))
            Logger.log('d', "Dot vector : {}".format(dv))  
            if dv > 0 :
                direction = 1
            else :
                direction = -1
                
            extents = mesh_data.getExtents()
            center = Vector(extents.center.x, extents.center.y, extents.center.z)

            # Get the Rotation Matrix
            rotation = Matrix()
            # setByRotationAxis or rotateByAxis ?  don't think there is a difference
            rotation.setByRotationAxis(direction*anGl, Vector(0, 1, 0))
            # Logger.log('d', "Rotation                 :\n{}".format(rotation))
            
            # Change Transfo data
            local_transformation = Matrix()      
            local_transformation.multiply(rotation)
            local_transformation.multiply(node.getLocalTransformation()) 
            # Log for debugging and Analyse           
            # Logger.log('d', "Local_transformation     :\n{}".format(node.getLocalTransformation())) 
            # Logger.log('d', "TransformMatrixOperation :\n{}".format(local_transformation))   
            # node.setTransformation(local_transformation)            
            op.addOperation(SetTransformMatrixOperation(node, local_transformation))

        op.push()
    
    def _unit_vector(self, vector):
        """ Returns the unit vector of the vector.  """
        return vector / numpy.linalg.norm(vector)

    def _angle_between(self, v1, v2):
        """ Returns the angle in radians between vectors 'v1' and 'v2'::
        """

        v1_u = self._unit_vector(v1)
        v2_u = self._unit_vector(v2)
        
        angle = numpy.arccos(numpy.clip(numpy.dot(v1_u, v2_u), -1.0, 1.0))
     
        return angle
 
    def _dot_vector(self, v1, v2):
        """ Returns the scalar product between vectors 'v1' and 'v2'::
        """

        v1_u = self._unit_vector(v1)
        v2_u = self._unit_vector(v2)
        
        dotv = numpy.dot(v1_u, v2_u)
     
        return dotv
        
    def doFastAutoOrientation(self):
        self._extended_mode=False
        self.doAutoOrientation(False)

    def doExtendedAutoOrientiation(self):
        self._extended_mode=True
        self.doAutoOrientation(True)

    def doAutoOrientation(self, extended_mode):
        # If we still had a message open from last time, hide it.
        if self._message:
            self._message.hide()

        selected_nodes = self._getSelectedNodes()
        if len(selected_nodes) == 0:
            return
        message = Message(i18n_catalog.i18nc("@info:status", "Calculating the optimal orientation..."), 0, False, -1, title = i18n_catalog.i18nc("@title", "Auto-Orientation"))
        message.show()

        job = CalculateOrientationJob(selected_nodes, extended_mode = extended_mode, message = message)
        job.finished.connect(self._onFinished)
        job.start()

    def _onFinished(self, job):
        if self._message:
            self._message.hide()

        if job.getMessage() is not None:
            job.getMessage().hide()
            if self._extended_mode :
                _text = i18n_catalog.i18nc("@info:status", "All selected objects have been oriented using the extended mode.")
            else :
                _text = i18n_catalog.i18nc("@info:status", "All selected objects have been oriented.")
            self._message = Message(_text, title=i18n_catalog.i18nc("@title", "Auto-Orientation"), message_type = Message.MessageType.POSITIVE)
            self._message.show()
