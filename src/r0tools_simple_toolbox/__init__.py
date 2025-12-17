bl_info = {
    "name": "r0Tools - Simple Toolbox.dev",
    "author": "Artur Rosário",
    "version": (0, 2, 0),
    "blender": (4, 2, 5),
    "location": "3D View > Simple Toolbox",
    "description": "Miscellaneous Utilities",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import importlib
import sys
from typing import List, Tuple

from . import utils as u  # isort: skip

modules = (
    ".addon_properties",
    ".addon_prefs",
    ".operators",
    ".menus",
    ".utils",
    ".ui",
    ".object_sets",
    ".vertex_groups",
    ".depsgraph",
    ".defines",
    ".repo.operators",
    ".repo.ui",
    ".data_ops",
    ".find_modifiers_ops",
    ".export_ops",
    ".keymaps",
)

_mod = "__INIT__"


def get_module_names() -> List[str]:
    """Get full module names including package"""
    return [f"{__package__}{module}" for module in modules]


def cleanup_modules():
    """Remove modules from sys.modules to ensure clean reload"""
    module_names = get_module_names()
    for module_name in module_names:
        if module_name in sys.modules:
            del sys.modules[module_name]
            if u.is_debug():
                print(f"[INFO] [{_mod}] Cleaned up module: {module_name}")


def import_modules() -> List[object]:
    """Import all modules and return them in a list"""
    module_objects = []
    for module in modules:
        try:
            imported_module = importlib.import_module(module, __package__)
            module_objects.append(imported_module)
            if u.is_debug():
                print(f"[INFO] [{_mod}] Imported: {imported_module.__name__}")
        except Exception as e:
            print(f"[ERROR] [{_mod}] Error importing {module}: {str(e)}")
    return module_objects


def reload_modules(module_objects: List[object]):
    """Reload all modules"""
    for module in module_objects:
        try:
            importlib.reload(module)
            if u.is_debug():
                print(f"[INFO] [{_mod}] Reloaded: {module.__name__}")
        except Exception as e:
            print(f"[ERROR] [{_mod}] Error reloading {module.__name__}: {str(e)}")


class AddonRegisterHelper:
    _instance = None
    modules: Tuple[object] = ()

    def __init__(self):
        cleanup_modules()
        self.modules = tuple(import_modules())
        reload_modules(self.modules)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self):
        """Register all modules"""
        print("\n-------------------------------------------------------------")
        print(f"Begin Addon Registration - r0fld4nc3 Simple Toolbox")

        for module in self.modules:
            if hasattr(module, "register"):
                try:
                    if u.is_debug():
                        print(f"[INFO] [{_mod}] Register module: {module.__name__}")
                    module.register()
                except Exception as e:
                    print(f"[ERROR] [{_mod}] Error registering module {module.__name__}: {str(e)}")

        print("-------------------------------------------------------------\n")

    def unregister(self):
        """Unregister all modules in reverse order"""
        print("\n-------------------------------------------------------------")
        print(f"Begin Addon Unregistration - r0fld4nc3 Simple Toolbox")

        for module in reversed(self.modules):
            if hasattr(module, "unregister"):
                try:
                    if u.is_debug():
                        print(f"[INFO] [{_mod}] Unregister module: {module.__name__}")
                    module.unregister()
                except Exception as e:
                    print(f"[ERROR] [{_mod}] Error unregistering module {module.__name__}: {str(e)}")

        print("-------------------------------------------------------------\n")


# Create global instance
addon_helper = AddonRegisterHelper.get_instance()


def register():
    addon_helper.register()


def unregister():
    addon_helper.unregister()


if __name__ == "__main__":
    register()
