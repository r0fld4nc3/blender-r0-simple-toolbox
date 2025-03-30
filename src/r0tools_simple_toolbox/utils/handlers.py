import bpy

from .. import utils as u
from ..operators import CustomTransformsOrientationsTracker
from .object_sets import refresh_object_sets_colours


@bpy.app.handlers.persistent
def handler_depsgraph_post_update(scene, depsgraph):
    """Handler that runs after depsgraph updates"""
    # Check specifically for object deletions
    if depsgraph.id_type_updated("OBJECT"):
        if u.IS_DEBUG():
            print("[DEBUG] [HANDLERS] Object updates detected")

        u.cleanup_object_set_invalid_references(scene)
        u.property_list_update(scene, bpy.context)


depsgraph_handlers = [handler_depsgraph_post_update]

load_post_handlers = [refresh_object_sets_colours]


def register():
    for handler in depsgraph_handlers:
        print(f"[HANDLERS] Registering {handler}")
        if handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(handler)

    for handler in load_post_handlers:
        print(f"[HANDLERS] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for handler in depsgraph_handlers:
        print(f"[HANDLERS] Unregister {handler}")
        if handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(handler)

    for handler in load_post_handlers:
        print(f"[HANDLERS] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)
