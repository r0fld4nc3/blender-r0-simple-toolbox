from pathlib import Path

from . import bl_info


def _version_str(version_tuple: tuple) -> str:
    v_str = ".".join([str(n) for n in version_tuple])
    return v_str


def _set_addon_internal_name(from_name: str) -> str:
    """
    Returns the correct internal name for use as bl_idname in AddonPreferences.
    For extensions Blender (4.2+), the add-on is registered under the full
    'bl_ext.<repo>.<name>' package path, so bl_idname MUST match that full path.
    For legacy add-ons, the bare module name is used.
    """

    if __package__ and __package__.startswith("bl_ext."):
        return __package__
    return from_name  # Original package name


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
