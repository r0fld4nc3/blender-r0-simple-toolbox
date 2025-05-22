import importlib
import sys

# Import order here is really important!
from .constants import *  # isort: skip
from .context import *  # isort: skip
from .custom_transform import *  # isort: skip
from .general import *  # isort: skip
from ..object_sets.object_sets import *  # isort: skip
from .vertex_groups import *  # isort: skip

package = __name__
module = "UTILS"

# fmt: off
# List of submodlules, keep in sync with imports
submodules = [
    "constants",
    "context",
    "custom_transform",
    "general",
    "object_sets",
    "vertex_groups",
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
            print(f"[{module}] Imported: {module.__name__}")
        except Exception as e:
            print(f"[{module}] Error importing {module_name}: {str(e)}")

    return _module_objects


def register():
    global _module_objects
    print("[{module}] Registering utility submodules")

    if not _module_objects:
        _import_submodules()

    for module in _module_objects:
        if hasattr(module, "register"):
            try:
                print(f"[{module}] Registering {module.__name__}")
                module.register()
            except Exception as e:
                print(f"[{module}] Error registering {module.__name__}: {str(e)}")


def unregister():
    global _module_objects
    print("[{module}] Unregistering utility submodules")

    for module in reversed(_module_objects):
        if hasattr(module, "register"):
            try:
                print(f"[{module}] Unregistering {module.__name__}")
                module.unregister()
            except Exception as e:
                print(f"[{module}] Error unregistering {module.__name__}: {str(e)}")
