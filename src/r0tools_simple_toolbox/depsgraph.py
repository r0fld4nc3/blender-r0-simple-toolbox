import bpy

from . import utils as u
from .operators import CustomTransformsOrientationsTracker

from .defines import DEBUG  # isort: skip

_mod = "DEPSGRAPH"

is_saving = False
is_updating = False  # Check if our depsgraph update is running


@bpy.app.handlers.persistent
def hanlder_on_save_pre(dummy):
    """Set the save lock before a file is saved."""
    global is_saving
    is_saving = True
    # print("Save Lock: ON")


@bpy.app.handlers.persistent
def hanlder_on_save_post(dummy):
    """Set the save lock after a file is saved."""
    global is_saving
    is_saving = False
    # print("Save Lock: OFF")


@bpy.app.handlers.persistent
def handler_depsgraph_post_update(scene, depsgraph):
    """Handler that runs after depsgraph updates"""

    boxcutter_running = u.boxcutter_running()

    if boxcutter_running:
        return None

    # Early exit if we're updating from our Depsgraph
    global is_updating
    if u.is_updating():
        print(f"[INFO] [{_mod}] Skipping depsgraph update as an update is already in progress.")
        return None
    else:
        is_updating = True

    # Early exit if saving, no need to check for context first
    if u.is_saving():
        print(f"[INFO] [{_mod}] Skipping depsgraph update on file save")
        return None

    # Check specifically for object changes
    if depsgraph.id_type_updated(u.DEPSGRAPH_ID_TYPES.OBJECT):
        if not u.is_writing_context_safe(scene):
            print(f"[WARNING] [{_mod}] Depsgraph writing context unsafe.")
            return None

        if u.object_count_changed():
            # u.timer_manager.schedule(u.cleanup_object_set_invalid_references, kwargs={"scene": scene}, delay=0, min_interval=0.1)
            u.cleanup_object_set_invalid_references(scene=scene)
            # u.timer_manager.schedule(u.handle_object_duplication_update, kwargs={"scene": scene}, delay=0, min_interval=0.1)
            u.handle_object_duplication_update(scene=scene)

        # u.object_sets_update_mesh_stats(depsgraph)

        # u.timer_manager.schedule(u.vertex_groups_list_update, kwargs={"scene": scene}, delay=0, min_interval=0.1)
        u.vertex_groups_list_update(scene=scene)

        # u.timer_manager.schedule(u.property_list_update, delay=0, min_interval=0.1)
        u.property_list_update(scene=scene)

    CustomTransformsOrientationsTracker.track_custom_orientations(
        scene,
    )

    is_updating = False


depsgraph_handlers = [handler_depsgraph_post_update]

load_post_handlers = [u.refresh_object_sets_colours]

save_pre_handlers = [hanlder_on_save_pre]
save_post_handlers = [hanlder_on_save_post]


def register():
    # Depsgraph Handlers
    for handler in depsgraph_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Registering {handler}")
        if handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(handler)

    # Save Pre Handlers
    for handler in save_pre_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register on_save_pre handler: {handler.__name__}")
        if handler not in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.append(handler)

    # Save Post Handlers
    for handler in save_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register on_save_post handler: {handler.__name__}")
        if handler not in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.append(handler)

    # Load Post Handlers
    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        if handler not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(handler)


def unregister():
    # Depsgraph Handlers
    for handler in depsgraph_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {handler}")
        if handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(handler)

    # Save Pre Handlers
    for handler in save_pre_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister on_save_pre handler: {handler.__name__}")
        if handler in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.remove(handler)

    # Save Post Handlers
    for handler in save_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister on_save_post handler: {handler.__name__}")
        if handler in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.remove(handler)

    # Load Post Handlers
    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        if handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(handler)
