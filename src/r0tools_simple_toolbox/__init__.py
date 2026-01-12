bl_info = {
    "name": "r0Tools - Simple Toolbox.dev",
    "author": "Artur Rosário",
    "version": (0, 3, 1),
    "blender": (4, 2, 5),
    "location": "3D View > Simple Toolbox",
    "description": "Miscellaneous Utilities",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import importlib

from . import utils as u  # isort: skip

_mod = "INIT"


# Thank you ACT plugin and how you do your load order
# This is directly inspired from you!
modules_load_order = (
    "addon_properties",
    "addon_prefs",
    "operators",
    "menus",
    "utils",
    "ui",
    "object_sets",
    "vertex_groups",
    "depsgraph",
    "defines",
    "repo.operators",
    "repo.ui",
    "data_ops",
    "find_modifiers_ops",
    "export_ops",
    "keymaps",
)

modules = [importlib.import_module(f".{name}", __package__) for name in modules_load_order]


def register():
    print("\n-------------------------------------------------------------")
    print(f"Begin Addon Registration - {bl_info.get('name')}")

    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()
            if u.is_debug():
                print(f"[INFO] [{_mod}] Registered: {mod.__name__}")

    print("-------------------------------------------------------------\n")


def unregister():
    print("\n-------------------------------------------------------------")
    print(f"Begin Addon Unregistration - {bl_info.get('name')}")

    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
            if u.is_debug():
                print(f"[INFO] [{_mod}] Registered: {mod.__name__}")

    print("-------------------------------------------------------------\n")


if __name__ == "__main__":
    register()
