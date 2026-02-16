from pathlib import Path

from . import bl_info


def _version_str(version_tuple: tuple):
    v_str = ".".join([str(n) for n in version_tuple])
    return v_str


def _set_addon_internal_name(from_name: str):
    """Utility function to set the constant addon Internal Name at startup.
    The issue stems from when the addon is an extension and the internal name becomes
    bl_ext.module_name.internal_name"""

    if __package__:
        split = __package__.split(".")
        if len(split) >= 3 and split[0].lower() == "bl_ext":  # Probably an extension
            for split_item in split:
                if from_name in split_item:
                    # Is an extension
                    return __package__

    # Extension name not found
    return from_name


# fmt: off
VERSION            = bl_info.get("version", (0, 0, 0))
VERSION_STR        = _version_str(VERSION)
BASE_NAME          = "r0tools_simple_toolbox"
ADDON_NAME         = bl_info.get("name")
ADDON_NAME_BARE    = "SimpleToolbox"
ADDON_BRANCH       = "main"
ADDON_CATEGORY     = "Simple Toolbox"
IDNAME_EXTRA       = '.' + ADDON_BRANCH if ADDON_BRANCH and ADDON_BRANCH.lower() != "main" else ''
INTERNAL_NAME      = _set_addon_internal_name(BASE_NAME)
REPO_NAME          = "r0Tools Extensions"
UPDATE_CHECK_CD    = 60  # seconds
TOOLBOX_PROPS_NAME = "r0fl_toolbox_props"
LOG_FILE           = Path(__file__).parent / "simple_toolbox.log"
# fmt: on
