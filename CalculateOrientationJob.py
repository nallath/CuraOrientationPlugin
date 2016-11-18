from UM.Job import Job
from .MeshTweaker import Tweak
from UM.Math.Quaternion import Quaternion
from UM.Math.Vector import Vector
from UM.Scene.SceneNode import SceneNode
import math

class CalculateOrientationJob(Job):
    def __init__(self, nodes):
        super().__init__()

        self._nodes = nodes
		
    def run(self):
        for node in self._nodes:
            transformed_vertices = node.getMeshDataTransformed().getVertices()

            result = Tweak(transformed_vertices, verbose=False)

            [v, phi] = result.Euler

            # Convert the new orientation into quaternion
            new_orientation = Quaternion.fromAngleAxis(phi, Vector(-v[0], -v[1], -v[2]))
            # Rotate the axis frame.
            rotation = Quaternion.fromAngleAxis(-0.5 * math.pi, Vector(1, 0, 0))
            new_orientation = rotation * new_orientation

            # Ensure node gets the new orientation
            node.rotate(new_orientation, SceneNode.TransformSpace.World)

            Job.yieldThread()
