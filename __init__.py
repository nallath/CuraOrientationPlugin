# Copyright (c) 2016 Jaime van Kessel
# The OrientationPLugin is released under the terms of the AGPLv3 or higher.

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("OrientationPlugin")

from . import OrientationPlugin

def getMetaData():
    return {}


def register(app):
    return {"extension": OrientationPlugin.OrientationPlugin()}
