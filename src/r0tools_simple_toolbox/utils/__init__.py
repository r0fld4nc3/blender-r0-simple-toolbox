import importlib
import logging

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
from ..export_ops.export_ops import * # isort: skip
# fmt: on

log = logging.getLogger(__name__)

# List of submodules, keep in sync with imports
modules_load_order = (
    "constants",
    "context",
    "custom_transform",
    "general",
    "defer",
    "edge_data",
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
