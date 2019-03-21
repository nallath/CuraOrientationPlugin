from UM.Extension import Extension
from UM.Scene.Selection import Selection



from UM.Message import Message

from .CalculateOrientationJob import CalculateOrientationJob

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("OrientationPlugin")


class OrientationPlugin(Extension):
    def __init__(self):
        super().__init__()
        self.addMenuItem(i18n_catalog.i18n("Calculate fast optimal printing orientation"), self.doFastAutoOrientation)
        self.addMenuItem(i18n_catalog.i18n("Calculate extended optimal printing orientation"), self.doExtendedAutoOrientiation)
        self._message = None

    def doFastAutoOrientation(self):
        self.doAutoOrientation(False)

    def doExtendedAutoOrientiation(self):
        self.doAutoOrientation(True)

    def doAutoOrientation(self, extended_mode):
        # If we still had a message open from last time, hide it.
        if self._message:
            self._message.hide()

        selected_nodes = Selection.getAllSelectedObjects()
        if len(selected_nodes) == 0:
            self._message = Message(i18n_catalog.i18nc("@info:status", "No objects selected to orient. Please select one or more objects and try again."), title = i18n_catalog.i18nc("@title", "Auto-Orientation"))
            self._message.show()
            return

        self._message = Message(i18n_catalog.i18nc("@info:status", "Calculating the optimal orientation..."), 0, False, -1, title = i18n_catalog.i18nc("@title", "Auto-Orientation"))
        self._message.show()

        job = CalculateOrientationJob(selected_nodes, extended_mode = extended_mode, message = self._message)
        job.finished.connect(self._onFinished)
        job.start()

    def _onFinished(self, job):
        if self._message:
            self._message.hide()
            self._message = Message(i18n_catalog.i18nc("@info:status", "All selected objects have been oriented."), title=i18n_catalog.i18nc("@title", "Auto-Orientation"))
            self._message.show()
