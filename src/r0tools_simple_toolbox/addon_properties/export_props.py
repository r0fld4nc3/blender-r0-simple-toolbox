import bpy
from bpy.props import (  # type: ignore
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from .. import utils as u
from ..defines import DEBUG

_mod = "EXPORT PROPS"


class r0SimpleToolboxExportProps(bpy.types.PropertyGroup):
    mkdirs_if_not_exist: BoolProperty(name="Create sub-paths", description="If chosen path does not exist in the filesystem, create the full path including sub-directories", default=False)  # type: ignore

    export_path: StringProperty(
        name="Path",
        description="Full filepath of file to be exported",
    )  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [r0SimpleToolboxExportProps]


load_post_handlers = []


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if DEBUG:
        print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_export_props")
    bpy.types.Scene.r0fl_toolbox_export_props = PointerProperty(type=r0SimpleToolboxExportProps)


def unregister():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")

    if DEBUG:
        print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_export_props")
    del bpy.types.Scene.r0fl_toolbox_export_props
