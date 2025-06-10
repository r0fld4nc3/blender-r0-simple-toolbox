import importlib
import sys

# Import order here is really important!
from .operators import *  # isort: skip

package = __name__
_mod = "OBJECT_SETS"

# fmt: off
# List of submodlules, keep in sync with imports
submodules = [
    "operators",
]
# fmt: on
_module_objects = []


def _import_submodules():
    global _module_objects

    for module_name in submodules:
        full_name = f"{package}.{module_name}"
        try:
            if full_name in sys.modules:
                # Already imported, get reference
                module = sys.modules[full_name]
            else:
                # Import new
                module = importlib.import_module(f".{module_name}", package)

            _module_objects.append(module)
            print(f"[INFO] [{_mod}] Imported: {module.__name__}")
        except Exception as e:
            print(f"[ERROR] [{_mod}] Error importing {module_name}: {str(e)}")

    return _module_objects


def register():
    global _module_objects
    print(f"[INFO] [{_mod}] Registering utility submodules")

    if not _module_objects:
        _import_submodules()

    for module in _module_objects:
        if hasattr(module, "register"):
            try:
                print(f"[INFO] [{_mod}] Registering {module.__name__}")
                module.register()
            except Exception as e:
                print(f"[ERROR] [{_mod}] Error registering {module.__name__}: {str(e)}")


def unregister():
    global _module_objects
    print(f"[INFO] [{_mod}]  Unregistering utility submodules")

    for module in reversed(_module_objects):
        if hasattr(module, "register"):
            try:
                print(f"[INFO] [{_mod}] Unregistering {module.__name__}")
                module.unregister()
            except Exception as e:
                print(f"[ERROR] [{_mod}] Error unregistering {module.__name__}: {str(e)}")
