import logging

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

log = logging.getLogger(__name__)


class r0SimpleToolboxExperimentalProps(bpy.types.PropertyGroup): ...


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [r0SimpleToolboxExperimentalProps]


load_post_handlers = []


def register():
    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)

    log.debug(f"Register bpy.types.Scene.r0fl_toolbox_experimental_props")
    bpy.types.Scene.r0fl_toolbox_experimental_props = PointerProperty(
        type=r0SimpleToolboxExperimentalProps, name="r0fl Toolbox Experimental"
    )

    for handler in load_post_handlers:
        log.debug(f"Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        log.debug(f"Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    log.debug(f"Unregister bpy.types.Scene.r0fl_toolbox_experimental_props")
    del bpy.types.Scene.r0fl_toolbox_experimental_props
