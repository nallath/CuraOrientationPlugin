from typing import List

from UM.Extension import Extension
from UM.PluginRegistry import PluginRegistry
from UM.Scene.SceneNode import SceneNode
from UM.Scene.Selection import Selection

from UM.Message import Message
from cura.CuraApplication import CuraApplication

from .CalculateOrientationJob import CalculateOrientationJob

from UM.i18n import i18nCatalog

import os
i18n_catalog = i18nCatalog("OrientationPlugin")


class OrientationPlugin(Extension):
    def __init__(self):
        super().__init__()
        self.addMenuItem(i18n_catalog.i18n("Calculate fast optimal printing orientation"), self.doFastAutoOrientation)
        self.addMenuItem(i18n_catalog.i18n("Calculate extended optimal printing orientation"), self.doExtendedAutoOrientiation)
        self.addMenuItem(i18n_catalog.i18n("Modify Settings"), self.showPopup)
        self._message = None

        self._currently_loading_files = []  # type: List[str]
        self._check_node_queue = []  # type: List[SceneNode]
        CuraApplication.getInstance().getPreferences().addPreference("OrientationPlugin/do_auto_orientation", False)
        self._do_auto_orientation = CuraApplication.getInstance().getPreferences().getValue("OrientationPlugin/do_auto_orientation")

        self._popup = None

        CuraApplication.getInstance().fileLoaded.connect(self._onFileLoaded)
        CuraApplication.getInstance().fileCompleted.connect(self._onFileCompleted)
        CuraApplication.getInstance().getController().getScene().sceneChanged.connect(self._onSceneChanged)
        CuraApplication.getInstance().getPreferences().preferenceChanged.connect(self._onPreferencesChanged)

    def _onPreferencesChanged(self, name: str) -> None:
        if name != "OrientationPlugin/do_auto_orientation":
            return
        self._do_auto_orientation = CuraApplication.getInstance().getPreferences().getValue("OrientationPlugin/do_auto_orientation")

    def _createPopup(self) -> None:
        # Create the plugin dialog component
        path = os.path.join(PluginRegistry.getInstance().getPluginPath("OrientationPlugin"), "SettingsPopup.qml")
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
            self._message = Message(i18n_catalog.i18nc("@info:status", "All selected objects have been oriented."),
                                    title=i18n_catalog.i18nc("@title", "Auto-Orientation"))
            self._message.show()
