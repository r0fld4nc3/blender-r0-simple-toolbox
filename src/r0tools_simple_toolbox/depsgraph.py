import bpy

from . import utils as u
from .operators import CustomTransformsOrientationsTracker

_mod = "DEPSGRAPH"


@bpy.app.handlers.persistent
def handler_depsgraph_post_update(scene, depsgraph):
    """Handler that runs after depsgraph updates"""

    # Check specifically for object deletions
    if depsgraph.id_type_updated(u.DEPSGRAPH_ID_TYPES.OBJECT):
        if not u.is_writing_context_safe(scene, check_addon_props=True):
            u.LOG(f"[INFO] [{_mod}] Avoided an addon write lock.")
            return None

        if u.object_count_changed():
            u.timer_manager.schedule(u.cleanup_object_set_invalid_references_o1, delay=0, min_interval=0.1)

        u.timer_manager.schedule(u.object_sets_update_mesh_stats, delay=0.5, min_interval=1)

        u.timer_manager.schedule(u.vertex_groups_list_update, delay=0, min_interval=0.05)

        u.property_list_update()
    CustomTransformsOrientationsTracker.track_custom_orientations(
        scene,
    )


depsgraph_handlers = [handler_depsgraph_post_update]

load_post_handlers = [u.refresh_object_sets_colours]


def register():
    for handler in depsgraph_handlers:
        print(f"[INFO] [{_mod}] Registering {handler}")
        if handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(handler)

    for handler in load_post_handlers:
        print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for handler in depsgraph_handlers:
        print(f"[INFO] [{_mod}] Unregister {handler}")
        if handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(handler)

    for handler in load_post_handlers:
        print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)
