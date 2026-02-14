bl_info = {
    "name": "r0Tools - Simple Toolbox.dev",
    "author": "Artur Rosário",
    "version": (0, 3, 2),
    "blender": (4, 2, 5),
    "location": "3D View > Simple Toolbox",
    "description": "Miscellaneous Utilities",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import importlib
import logging

from . import settings
from . import utils as u
from .logs import configure_logging, reset_log_file, set_root_logger_level

# Thank you ACT plugin and how you do your load order
# This is directly inspired from you!
modules_load_order = (
    "addon_properties",
    "addon_prefs",
    "msgbus",
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
    from .defines import (
        ADDON_BRANCH,
        ADDON_NAME_BARE,
        IDNAME_EXTRA,
        INTERNAL_NAME,
        LOG_FILE,
        VERSION,
    )

    # Initialise settings
    settings_mgr = settings.init_settings_manager()

    configure_logging(LOG_FILE)
    reset_log_file(LOG_FILE)

    # Update logging level
    if settings_mgr.settings.debug:
        log.info("Set logging mode: DEBUG")
        set_root_logger_level(logging.DEBUG)

    log.info("-------------------------------------------------------------")
    log.info(f"{ADDON_NAME_BARE}{IDNAME_EXTRA}")
    log.info(f"Version: {VERSION}")
    log.info(f"Branch: {ADDON_BRANCH}")
    log.info(f"Internal Name: {INTERNAL_NAME}")
    log.info(f"Log: {LOG_FILE}")

    log.info(f"Begin Addon Registration - {bl_info.get('name')}")

    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()

            # Update addon prefs based on settings after registering
            if "addon_prefs" in mod.__name__:
                addon_prefs = u.get_addon_prefs()
                addon_prefs.debug = settings_mgr.settings.debug

            log.debug(f"Registered: {mod.__name__}")

    log.info("-------------------------------------------------------------")


def unregister():
    log.info("-------------------------------------------------------------")
    log.info(f"Begin Addon Unregistration - {bl_info.get('name')}")

    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
            log.debug(f"Registered: {mod.__name__}")

    log.info("-------------------------------------------------------------")


if __name__ == "__main__":
    register()
