import importlib
import logging

# Import order here is really important!
from .find_modifiers_operators import *  # isort: skip
from .. import utils as u  # isort: skip

package = __name__

log = logging.getLogger(__name__)

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
            log.debug(f"Registered: {mod.__name__}")


def unregister():
    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
            log.debug(f"Unregistered: {mod.__name__}")
