from UM.Job import Job
from UM.Operations.GroupedOperation import GroupedOperation
from UM.Operations.RotateOperation import RotateOperation
from cura.CuraApplication import CuraApplication
from .MeshTweaker import Tweak
from UM.Math.Quaternion import Quaternion
from UM.Math.Vector import Vector
from UM.Scene.SceneNode import SceneNode
import math

from typing import List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from UM.Message import Message


class CalculateOrientationJob(Job):
    def __init__(self, nodes: List[SceneNode], extended_mode: bool = False, message: Optional["Message"] = None) -> None:
        super().__init__()
        self._message = message
        self._nodes = nodes
        self._extended_mode = extended_mode

    def run(self) -> None:
        op = GroupedOperation()

        for node in self._nodes:
            transformed_vertices = node.getMeshDataTransformed().getVertices()

            result = Tweak(transformed_vertices, extended_mode = self._extended_mode, verbose=False, progress_callback=self.updateProgress, min_volume=CuraApplication.getInstance().getPreferences().getValue("OrientationPlugin/min_volume"))

            [v, phi] = result.euler_parameter

            # Convert the new orientation into quaternion
            new_orientation = Quaternion.fromAngleAxis(phi, Vector(-v[0], -v[1], -v[2]))
            # Rotate the axis frame.
            rotation = Quaternion.fromAngleAxis(-0.5 * math.pi, Vector(1, 0, 0))
            new_orientation = rotation * new_orientation

            # Ensure node gets the new orientation, and rotate it around the center of the object.
            # The rotating around the center prevents it from getting all kinds of weird new positions on the buildplate
            op.addOperation(RotateOperation(node, new_orientation, rotate_around_point = node.getBoundingBox().center))

            Job.yieldThread()
        op.push()

    def updateProgress(self, progress):
        if self._message:
            self._message.setProgress(progress)

    def getMessage(self) -> Optional["Message"]:
        return self._message