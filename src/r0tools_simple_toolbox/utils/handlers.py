import bpy

from r0tools_simple_toolbox import utils as u
from r0tools_simple_toolbox.operators import CustomTransformsOrientationsTracker


@bpy.app.handlers.persistent
def handler_depsgraph_post_update(scene, depsgraph):
    """Handler that runs after depsgraph updates"""
    # Check specifically for object deletions
    if depsgraph.id_type_updated("OBJECT"):
        if u.IS_DEBUG():
            print("[DEBUG][HANDLERS] Object updates detected")

        u.cleanup_object_set_invalid_references(scene)
        u.property_list_update(scene, bpy.context)


@bpy.app.handlers.persistent
def refresh_object_sets_colours(context):
    """Refresh colors for all object sets"""
    if u.IS_DEBUG():
        print("[OBJECT_SETS] Force Refreshing Object Sets' Colours")
    addon_prefs = u.get_addon_prefs()
    addon_props = u.get_addon_props()
    object_sets = addon_props.object_sets

    if not addon_prefs.object_sets_use_colour:
        return

    for object_set in object_sets:
        if u.IS_DEBUG():
            print(f"[DEBUG] Refresh: {object_set.name}")
        object_set.update_object_set_colour(context)


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
