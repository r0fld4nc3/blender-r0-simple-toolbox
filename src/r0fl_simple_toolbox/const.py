from . import bl_info

def _version_str(version_tuple: tuple):
    v_str = '.'.join([str(n) for n in version_tuple])
    return v_str

VERSION = bl_info.get("version", (0, 0, 0))
VERSION_STR = _version_str(VERSION)
ADDON_NAME = bl_info.get("name")
INTERNAL_NAME = "r0fl_simple_toolbox"
DEBUG = True
