# Copyright (c) 2016 Jaime van Kessel
# The OrientationPLugin is released under the terms of the AGPLv3 or higher.

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("OrientationPlugin")

from . import OrientationPlugin

def getMetaData():
    return {
        "type": "extension",
        "plugin":
        {
            "name": "OrientationPlugin",
            "author": "Jaime van Kessel",
            "version": "2.3",
            "api": 3,
            "description": i18n_catalog.i18nc("Description of plugin", "Extension that wraps the MeshTweaker by Christoph Schranz, so it can easily be used in Cura")
        }
    }


def register(app):
    return {"extension": OrientationPlugin.OrientationPlugin()}
