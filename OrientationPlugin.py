from UM.Extension import Extension
from UM.Scene.Selection import Selection



from UM.Message import Message

from .CalculateOrientationJob import CalculateOrientationJob

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("OrientationPlugin")


class OrientationPlugin(Extension):
    def __init__(self):
        super().__init__()
        self.addMenuItem(i18n_catalog.i18n("Calculate optimal printing orientation"), self.doAutoOrientation)
        self._message = None

    def doAutoOrientation(self):
        selected_nodes = Selection.getAllSelectedObjects()
        self._message = Message(i18n_catalog.i18nc("@info:status", "Calculating optimal orientation"), 0, False, -1)
        self._message.show()

        job = CalculateOrientationJob(selected_nodes)
        job.finished.connect(self._onFinished)
        job.start()

    def _onFinished(self, job):
        if self._message:
            self._message.hide()