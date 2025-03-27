import bpy

from . import utils as u

# from .operators import CustomTransformsOrientationsTracker


# Consider creating a "delay_execution" function and running each of these from a bpy.app.timer
# The aim is to try and fix some stuttering when there are several hundreds or more objects in
# the scene.
"""
def delay_execution(func, delay=0, persistent=False):
    if bpy.app.timers.is_registered(func):
        bpy.app.timers.unregister(func)

    bpy.app.timers.register(func, first_interval=delay, persistent=persistent)
"""


@bpy.app.handlers.persistent
def handler_depsgraph_post_update(scene, depsgraph):
    """Handler that runs after depsgraph updates"""
    # Check specifically for object deletions
    if depsgraph.id_type_updated("OBJECT"):
        if u.IS_DEBUG():
            print("[DEBUG] [DEPSGRAPH] Object updates detected")

        u.cleanup_object_set_invalid_references(scene)
        u.property_list_update(scene, bpy.context)


@bpy.app.handlers.persistent
def refresh_object_sets_colours(context):
    """Refresh colors for all object sets"""
    if u.IS_DEBUG():
        print("[DEPSGRAPH] Force Refreshing Object Sets' Colours")
    addon_prefs = u.get_addon_prefs()
    addon_props = u.get_addon_props()
    object_sets = addon_props.object_sets

    if not addon_prefs.object_sets_use_colour:
        return

    for object_set in object_sets:
        if u.IS_DEBUG():
            print(f"[DEBUG] [DEPSGRAPH] Refresh: {object_set.name}")
        object_set.update_object_set_colour(context)


depsgraph_handlers = [handler_depsgraph_post_update]

load_post_handlers = [refresh_object_sets_colours]


def register():
    for handler in depsgraph_handlers:
        print(f"[DEPSGRAPH] Registering {handler}")
        if handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(handler)

    for handler in load_post_handlers:
        print(f"[DEPSGRAPH] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for handler in depsgraph_handlers:
        print(f"[DEPSGRAPH] Unregister {handler}")
        if handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(handler)

    for handler in load_post_handlers:
        print(f"[DEPSGRAPH] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)
