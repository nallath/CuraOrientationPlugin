// Copyright (c) 2022 Jaime van Kessel

import QtQuick 6.0
import QtQuick.Controls 6.0

import UM 1.6 as UM


UM.Dialog
{
    minimumWidth: 450
    minimumHeight: 100
    function boolCheck(value) //Hack to ensure a good match between python and qml.
    {
        if(value == "True")
        {
            return true
        }else if(value == "False" || value == undefined)
        {
            return false
        }
        else
        {
            return value
        }
    }

    property variant i18n_catalog: UM.I18nCatalog { name: "OrientationPlugin" }
	
    title: i18n_catalog.i18nc("@title", "Auto orientation plugin settings")

    UM.CheckBox
    {
        checked: boolCheck(UM.Preferences.getValue("OrientationPlugin/do_auto_orientation"))
        onClicked: UM.Preferences.setValue("OrientationPlugin/do_auto_orientation", checked)

        text: i18n_catalog.i18nc("@label", "Automatically calculate the orientation for all loaded models")
    }
	
}