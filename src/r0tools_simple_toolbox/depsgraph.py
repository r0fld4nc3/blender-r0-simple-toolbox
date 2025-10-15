import bpy

from . import utils as u
from .operators import CustomTransformsOrientationsTracker

_mod = "DEPSGRAPH"

is_saving = False
is_updating = False  # Check if our depsgraph update is running


@bpy.app.handlers.persistent
def handler_on_save_pre(dummy):
    """Set the save lock before a file is saved."""
    global is_saving
    is_saving = True
    # print("Save Lock: ON")


@bpy.app.handlers.persistent
def handler_on_save_post(dummy):
    """Set the save lock after a file is saved."""
    global is_saving
    is_saving = False
    # print("Save Lock: OFF")


@bpy.app.handlers.persistent
def handler_depsgraph_post_update(scene, depsgraph):
    # Early exit if saving, no need to check for context first
    if u.is_saving():
        print(f"[INFO] [{_mod}] Skipping scheduled depsgraph update on file save")
        return None

    # Early exit if we're updating from our Depsgraph
    if u.is_updating():
        u.log(f"[INFO] [{_mod}] Skipping scheduled depsgraph update: Update already in progress.")
        return None

    # Check if any running modal operators - also important in the scheduled function
    modal_ops = u.get_active_modal_operators()
    if modal_ops:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Skipping scheduled depsgraph update: Active Modal Operators running.")
            for op in modal_ops:
                print(f"{op.bl_idname}")
        return None

    # Check specifically for object changes
    if depsgraph.id_type_updated(u.DEPSGRAPH_ID_TYPES.OBJECT):
        u.set_is_updating(True)

        try:
            if u.object_count_changed():
                u.cleanup_object_set_invalid_references(scene=scene)
                u.handle_object_duplication_update(scene=scene)

            # u.object_sets_update_mesh_stats(depsgraph)

            # bpy.ops.r0tools.vertex_groups_list_update()
            u.vertex_groups_list_update(scene=scene)

            u.property_list_update(scene=scene)

            u.object_attributes_list_update(scene=scene)

            CustomTransformsOrientationsTracker.track_custom_orientations(scene)
        except Exception as e:
            print(f"[ERROR] [{_mod}] {e}")
        finally:
            # Ensure flag is always reset
            u.set_is_updating(False)

        return None  # Return None for timer


depsgraph_handlers = [handler_depsgraph_post_update]

load_post_handlers = [u.refresh_object_sets_colours]

save_pre_handlers = [handler_on_save_pre]
save_post_handlers = [handler_on_save_post]


def register():
    # Depsgraph Handlers
    for handler in depsgraph_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Registering {handler}")
        if handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(handler)

    # Save Pre Handlers
    for handler in save_pre_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register on_save_pre handler: {handler.__name__}")
        if handler not in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.append(handler)

    # Save Post Handlers
    for handler in save_post_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register on_save_post handler: {handler.__name__}")
        if handler not in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.append(handler)

    # Load Post Handlers
    for handler in load_post_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        if handler not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(handler)


def unregister():
    # Depsgraph Handlers
    for handler in depsgraph_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister {handler}")
        if handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(handler)

    # Save Pre Handlers
    for handler in save_pre_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister on_save_pre handler: {handler.__name__}")
        if handler in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.remove(handler)

    # Save Post Handlers
    for handler in save_post_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister on_save_post handler: {handler.__name__}")
        if handler in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.remove(handler)

    # Load Post Handlers
    for handler in load_post_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        if handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(handler)
