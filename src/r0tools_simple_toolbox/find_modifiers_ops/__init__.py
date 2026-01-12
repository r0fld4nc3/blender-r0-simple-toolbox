import importlib

# Import order here is really important!
from .find_modifiers_operators import *  # isort: skip
from .. import utils as u  # isort: skip

package = __name__
_mod = "FIND_MODIFIER_OPS"

# List of submodules, keep in sync with imports
submodules = [
    "find_modifiers_operators",
]
modules_load_order = ("find_modifiers_operators",)

modules = [importlib.import_module(f".{name}", __package__) for name in modules_load_order]


def register():
    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()
            if u.is_debug():
                print(f"[INFO] [{_mod}] Registered: {mod.__name__}")


def unregister():
    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
            if u.is_debug():
                print(f"[INFO] [{_mod}] Unregistered: {mod.__name__}")
