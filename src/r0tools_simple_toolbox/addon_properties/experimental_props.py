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

_mod = "EXPERIMENTAL PROPS"


class r0SimpleToolboxExperimentalProps(bpy.types.PropertyGroup):
    show_edge_data_ops: BoolProperty(
        name="Edge Data Ops", description="Toggle visibility of experimental Edge Data Operators", default=True
    )  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [r0SimpleToolboxExperimentalProps]


load_post_handlers = []


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if DEBUG:
        print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_experimental_props")
    bpy.types.Scene.r0fl_toolbox_experimental_props = PointerProperty(type=r0SimpleToolboxExperimentalProps)

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
        print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_experimental_props")
    del bpy.types.Scene.r0fl_toolbox_experimental_props
