project(CuraOrientationPlugin NONE)

cmake_minimum_required(VERSION 3.0.0)

install(FILES
	plugin.json
    CalculateOrientationJob.py
    LICENSE
    MeshTweaker.py
    OrientationPlugin.py
    README.md
    __init__.py
    DESTINATION lib/cura/plugins/OrientationPlugin
)
