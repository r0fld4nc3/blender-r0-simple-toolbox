import importlib
import logging

# Import order here is really important!
from .edge_data_operators import *  # isort: skip
from .. import utils as u  # isort: skip

log = logging.getLogger(__name__)

modules_load_order = (
    "data_operators",
    "edge_data_operators",
    "ui",
)

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
