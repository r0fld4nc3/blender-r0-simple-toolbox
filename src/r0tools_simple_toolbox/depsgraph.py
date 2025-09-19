import bpy

from . import utils as u
from .operators import CustomTransformsOrientationsTracker

from .defines import DEBUG  # isort: skip

_mod = "DEPSGRAPH"


@bpy.app.handlers.persistent
def handler_depsgraph_post_update(scene, depsgraph):
    """Handler that runs after depsgraph updates"""

    boxcutter_running = u.boxcutter_running()

    if boxcutter_running:
        return None

    # Check specifically for object changes
    if depsgraph.id_type_updated(u.DEPSGRAPH_ID_TYPES.OBJECT):
        if not u.is_writing_context_safe(scene):
            print(f"[WARNING] [{_mod}] Depsgraph writing context unsafe.")
            return None

        if u.object_count_changed():
            u.timer_manager.schedule(u.cleanup_object_set_invalid_references, delay=0, min_interval=0.1)
            # u.cleanup_object_set_invalid_references()
            u.timer_manager.schedule(u.handle_object_duplication_update, delay=0, min_interval=0.1)
            # u.handle_object_duplication_update()

        # u.object_sets_update_mesh_stats(depsgraph)

        u.timer_manager.schedule(u.vertex_groups_list_update, delay=0, min_interval=0.1)
        # u.vertex_groups_list_update()

        u.timer_manager.schedule(u.property_list_update, delay=0, min_interval=0.1)
        # u.property_list_update()

    CustomTransformsOrientationsTracker.track_custom_orientations(
        scene,
    )


depsgraph_handlers = [handler_depsgraph_post_update]

load_post_handlers = [u.refresh_object_sets_colours]


def register():
    for handler in depsgraph_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Registering {handler}")
        if handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(handler)

    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for handler in depsgraph_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {handler}")
        if handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(handler)

    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)
