import importlib
import sys

# Import order here is really important!
# fmt: off
from .constants import *  # isort: skip
from .context import *  # isort: skip
from .custom_transform import *  # isort: skip
from .general import *  # isort: skip
from ..object_sets.object_sets import *  # isort: skip
from ..vertex_groups.vertex_groups import *  # isort: skip
from .defer import timer_manager, deferred  # isort: skip
from .edge_data import (  # isort: skip
    initialize_bweight_presets,
)
from .boxcutter import get_boxcutter_props, boxcutter_running  # isort: skip
from ..export_ops.export_ops import * # isort: skip
from ..defines import DEBUG # isort: skip
# fmt: on

package = __name__
_mod = "UTILS.__INIT__"

# fmt: off
# List of submodules, keep in sync with imports
submodules = [
    "constants",
    "context",
    "custom_transform",
    "general",
    "defer",
    "edge_data",
    "boxcutter",
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
            if DEBUG:
                print(f"[INFO] [{_mod}] Imported: {module.__name__}")
        except Exception as e:
            print(f"[ERROR] [{_mod}] Error importing {module_name}: {str(e)}")

    return _module_objects


def register():
    global _module_objects

    if not _module_objects:
        _import_submodules()

    for module in _module_objects:
        if hasattr(module, "register"):
            try:
                if DEBUG:
                    print(f"[INFO] [{_mod}] Registering {module.__name__}")
                module.register()
            except Exception as e:
                print(f"[ERROR] [{_mod}] Error registering {module.__name__}: {str(e)}")


def unregister():
    global _module_objects

    for module in reversed(_module_objects):
        if hasattr(module, "register"):
            try:
                if DEBUG:
                    print(f"[INFO] [{_mod}] Unregistering {module.__name__}")
                module.unregister()
            except Exception as e:
                print(f"[ERROR] [{_mod}] Error unregistering {module.__name__}: {str(e)}")
