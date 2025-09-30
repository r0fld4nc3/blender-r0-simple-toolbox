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

_mod = "OBJECT PROPS"


class R0PROP_PG_ObjectSetUUID(bpy.types.PropertyGroup):
    uuid: bpy.props.StringProperty(name="Set UUID")  # type: ignore


class r0SimpleToolboxObjectProps(bpy.types.PropertyGroup):
    """Object-level properties for Simple Toolbox"""

    object_sets: bpy.props.CollectionProperty(type=R0PROP_PG_ObjectSetUUID)  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_PG_ObjectSetUUID,
    r0SimpleToolboxObjectProps,
]


load_post_handlers = []


def register():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if u.is_debug():
        print(f"[INFO] [{_mod}] Register bpy.types.Object.r0fl_toolbox_props")
    bpy.types.Object.r0fl_toolbox_props = PointerProperty(type=r0SimpleToolboxObjectProps, name="ToolboxObject")

    for handler in load_post_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    if u.is_debug():
        print(f"[INFO] [{_mod}] Unregister bpy.types.Object.r0fl_toolbox_props")
    del bpy.types.Object.r0fl_toolbox_props
