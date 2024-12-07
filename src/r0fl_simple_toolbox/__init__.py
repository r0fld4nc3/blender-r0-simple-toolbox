bl_info = {
    "name": "r0Tools - Simple Toolbox",
    "author": "Artur Rosário",
    "version": (0, 0, 13),
    "blender": (4, 2, 1),
    "location": "3D View > Tool",
    "description": "Miscellaneous Utilities",
    "warning": "",
    "doc_url": "",
    "category": "Object"
}

import importlib

modules = (
    ".properties",
    ".operators",
    ".ui",
)

def import_modules():
    for module in modules:
        print(f"------------------> IMPORT {module} - {__package__}")
        importlib.import_module(module, __package__)


def reimport_modules():
    for module in modules:
        print(f"------------------> RELOAD {module} - {__package__}")
        to_reload_module = importlib.import_module(module, __package__)
        importlib.reload(to_reload_module)


import_modules()
reimport_modules()

from . import properties
from . import operators
from . import ui

register_modules = [
    properties,
    operators,
    ui,
]


def register():
    for module in register_modules:
        module.register()


def unregister():
    for module in register_modules:
        module.unregister()


if __name__ == "__main__":
    register()
