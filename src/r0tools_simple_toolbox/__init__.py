bl_info = {
    "name": "r0Tools - Simple Toolbox.dev",
    "author": "Artur Rosário",
    "version": (0, 4, 0),
    "blender": (4, 2, 5),
    "location": "3D View > Simple Toolbox",
    "description": "Miscellaneous Utilities",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import importlib
import logging
from pathlib import Path

from . import utils as u
from .logs import configure_logging, reset_log_file

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

log = logging.getLogger(__name__)


def register():
    from .defines import LOG_FILE

    configure_logging(LOG_FILE)
    reset_log_file(LOG_FILE)

    log.info("-------------------------------------------------------------")
    log.info(f"Begin Addon Registration - {bl_info.get('name')}")

    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()
            if u.is_debug():
                log.debug(f"Registered: {mod.__name__}")

    log.info("-------------------------------------------------------------")


def unregister():
    log.info("-------------------------------------------------------------")
    log.info(f"Begin Addon Unregistration - {bl_info.get('name')}")

    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
            if u.is_debug():
                log.debug(f"Registered: {mod.__name__}")

    log.info("-------------------------------------------------------------")


if __name__ == "__main__":
    register()
