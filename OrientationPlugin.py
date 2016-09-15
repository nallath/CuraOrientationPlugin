from UM.Extension import Extension
from UM.Scene.Selection import Selection

from UM.Math.Vector import Vector
from UM.Math.Quaternion import Quaternion
from UM.Math.Matrix import Matrix
from UM.Scene.SceneNode import SceneNode
from .MeshTweaker import Tweak

import math

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("OrientationPlugin")


class OrientationPlugin(Extension):
    def __init__(self):
        super().__init__()
        self.addMenuItem(i18n_catalog.i18n("Calculate optimal printing orientation"), self.doAutoOrientation)

    def doAutoOrientation(self):
        selected_nodes = Selection.getAllSelectedObjects()
        for node in selected_nodes:
            transformed_vertices = node.getMeshDataTransformed().getVertices()
            result = Tweak(transformed_vertices, bi_algorithmic = True, verbose = False)

            # Convert the new orientation into quaternion
            new_orientation = Quaternion.fromAngleAxis(result.phi, Vector(-result.v[0], -result.v[1], -result.v[2]))
            # Rotate the axis frame.
            rotation = Quaternion.fromAngleAxis(-0.5 * math.pi, Vector(1, 0, 0))
            new_orientation = rotation * new_orientation

            # Ensure node gets the new orientation
            node.rotate(new_orientation, SceneNode.TransformSpace.World)