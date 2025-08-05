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

_mod = "ATTRIBUTES PROPS"


class r0SimpleToolboxAttributesProps(bpy.types.PropertyGroup): ...


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [r0SimpleToolboxAttributesProps]


load_post_handlers = []


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if DEBUG:
        print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_attributes_props")
    bpy.types.Scene.r0fl_toolbox_attributes_props = PointerProperty(type=r0SimpleToolboxAttributesProps)

    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    if DEBUG:
        print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_attributes_props")
    del bpy.types.Scene.r0fl_toolbox_attributes_props
