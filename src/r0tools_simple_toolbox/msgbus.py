import logging

import bpy

from . import utils as u
from .object_sets import pending_known_objects
from .operators import CustomTransformsOrientationsTracker
from .vertex_groups import vertex_groups_list_update

log = logging.getLogger(__name__)

_msgbus_owner = object()

_pending_updates = {
    "vertex_groups": False,
    "properties": False,
    "attributes": False,
    "objects": False,
}

_last_selection_hash = None


# ============================================================================
# Main Subscription Manager
# ============================================================================


def subscribe_to_all_changes():
    """
    Master subscription function - subscribes to all data changes needed.
    """
    log.debug("Establishing msgbus subscriptions...")

    # Clear any existing subscriptions
    bpy.msgbus.clear_by_owner(_msgbus_owner)

    # Subscribe to different data types
    _subscribe_to_selection_changes()

    log.debug("All msgbus subscriptions established")


# ============================================================================
# Selection & Vertex Groups
# ============================================================================


def _subscribe_to_selection_changes():
    """Subscribe to active object and selection changes"""

    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=_msgbus_owner,
        args=(),
        notify=_on_selection_changed,
    )

    log.debug("Subscribed to active object changes")


def _subscribe_to_object_vertex_groups(obj):
    """Subscribe to vertex group changes on specific object"""
    try:
        bpy.msgbus.subscribe_rna(
            key=obj.path_resolve("vertex_groups", False),
            owner=_msgbus_owner,
            args=(obj,),
            notify=_on_vertex_groups_modified,
        )
    except Exception as e:
        log.warning(f"Unable to subscribe to vertex groups on {obj.name}: {e}")


# ============================================================================
# Msgbus Callbacks
# ============================================================================


def _on_selection_changed():
    """Selection changed callback"""
    log.debug("Selection changed")

    selected_objects = u.get_selected_objects()

    # Re-subscribe to vertex groups on new selected objects
    for obj in selected_objects:
        _subscribe_to_object_vertex_groups(obj)

    # Update selection hash
    global _last_selection_hash
    _last_selection_hash = _compute_selection_hash()

    # Schedule updates
    _pending_updates["vertex_groups"] = True
    _pending_updates["properties"] = True
    _pending_updates["attributes"] = True

    if u.object_count_changed():
        _pending_updates["objects"] = True

    schedule_deferred_update()


def _on_vertex_groups_modified(obj):
    """Callback when vertex groups are added/removed/renamed on an object"""

    log.debug(f"Vertex groups modified on {obj.name}")

    if obj in u.get_selected_objects():
        _pending_updates["vertex_groups"] = True
        schedule_deferred_update()


def _process_new_objects_stage():
    """
    Process and stage any new known objects in the scene.
    This needs to be captured in the depsgraph update and
    not already in the scheduled function for the pointer
    and object snapshot to be valid (while it's hot).

    It diffs the current known (synced pointers) with any new
    unknown pointers and stages (pushes) these objects to process
    to object_sets' staging list.

    This list is then consumed on process.
    """
    new_objects = u.get_new_objects()

    if new_objects:
        # Push new object changes to object_sets' new_objects list
        log.debug(f"Staging {len(new_objects)} new object(s) for processing")
        pending_known_objects.extend(new_objects)

    u.sync_known_objects()


# ============================================================================
# Depsgraph Fallback (Read-Only Detection Only)
# ============================================================================


@bpy.app.handlers.persistent
def on_depsgraph_update_post(scene, depsgraph):
    if u.is_saving() or u.is_updating():
        return

    global _last_selection_hash
    current_hash = _compute_selection_hash()

    if current_hash != _last_selection_hash:
        log.debug("Selection changed (depsgraph fallback)")
        _last_selection_hash = current_hash

        # Re-subscribe to vertex groups for the new selections
        for obj in u.get_selected_objects():
            _subscribe_to_object_vertex_groups(obj)

        # Set update flags
        _pending_updates["vertex_groups"] = True
        _pending_updates["properties"] = True
        _pending_updates["attributes"] = True
        schedule_deferred_update()

    if depsgraph.id_type_updated(u.DEPSGRAPH_ID_TYPES.OBJECT):
        if u.object_count_changed():
            log.debug("Object count changed (depsgraph)")
            _pending_updates["objects"] = True
            _process_new_objects_stage()
            schedule_deferred_update()


def _compute_selection_hash():
    try:
        selected = tuple(sorted(obj.name for obj in u.get_selected_objects()))
        active_object = u.get_active_object()
        active_name = active_object.name if active_object else None
        return hash((selected, active_name))
    except Exception:
        return None


# ============================================================================
# Deferred Update Processing
# ============================================================================


def schedule_deferred_update():
    """Schedule update via timer - ONLY safe way to write ID properties."""
    if not bpy.app.timers.is_registered(_deferred_update):
        bpy.app.timers.register(_deferred_update, first_interval=0.0)


def _deferred_update():
    """
    Timer callback - run outside depsgraph evaluation.
    Returns a float to reschedule if context is still unsafe,
    or None to stop repeating once updates are processed.
    """
    scene = u.get_scene()

    # If context is not write-safe yet, reschedule rather than drop the update
    if scene is None or not u.is_writing_context_safe(scene):
        log.warning("Deferred update: context not write-safe, rescheduling in 100ms")
        return 0.1

    process_pending_updates()
    return None


def process_pending_updates():
    """
    Process all pending updates in one batch.
    Only called from a write-safe context.
    """

    if u.is_saving():
        log.debug("Skipping updates: file is saving")
        return

    if u.is_updating():
        log.debug("Skipping updates: update already in progress")
        return

    # Redundant safety check
    scene = u.get_scene()
    if scene is None or not u.is_writing_context_safe(scene):
        log.warning("process_pending_updates: write context not safe, aborting")
        return

    if not any(_pending_updates.values()):
        log.debug("No pending updates to process.")
        return

    try:
        u.set_is_updating(True)

        # Vertex groups update
        if _pending_updates["vertex_groups"]:
            vertex_groups_list_update(scene=scene, force=True)
            _pending_updates["vertex_groups"] = False

        # Objects update
        if _pending_updates["objects"]:
            u.cleanup_object_set_invalid_references(scene=scene)
            u.handle_object_duplication_update(scene=scene)
            _pending_updates["objects"] = False

        # Properties update
        if _pending_updates["properties"]:
            u.property_list_update(scene=scene)
            _pending_updates["properties"] = False

        # Attributes update
        if _pending_updates["attributes"]:
            u.object_attributes_list_update(scene=scene)
            _pending_updates["attributes"] = False

        CustomTransformsOrientationsTracker.track_custom_orientations(scene)

    except Exception as e:
        log.error(f"Error processing updates: {e}")
        u.context_error_debug(error=e)
    finally:
        u.set_is_updating(False)


def cancel_pending_updates():
    """
    Cancel any queued timer and clear all pending flags.
    Called externally by depsgraph save handlers to ensure
    the timer cannot fire during a restricted write context.
    """

    if bpy.app.timers.is_registered(_deferred_update):
        bpy.app.timers.unergister(_deferred_update)

    global _pending_updates
    _pending_updates = {key: False for key in _pending_updates}
    log.debug("Pending updates cancelled.")


def resync_selection_hash():
    """
    Recompute and store the current selection hash after a save.
    Prevents the first post-save depsgraph tick from triggering
    an update due to a stale hash.
    """

    global _last_selection_hash
    _last_selection_hash = _compute_selection_hash()
    log.debug("Selection hash resynced after save.")


# ============================================================================
# Application Handlers
# ============================================================================


@bpy.app.handlers.persistent
def on_load_post(dummy):
    log.debug("Load post - establishing subscriptions")
    global _last_selection_hash
    _last_selection_hash = _compute_selection_hash()
    subscribe_to_all_changes()


@bpy.app.handlers.persistent
def on_undo_redo_post(dummy):
    log.debug("Undo/Redo post")
    if u.object_count_changed():
        _pending_updates["properties"] = True
        _pending_updates["attributes"] = True
        _pending_updates["objects"] = True
        schedule_deferred_update()
    subscribe_to_all_changes()


_handlers = [
    (bpy.app.handlers.load_post, on_load_post),
    (bpy.app.handlers.undo_post, on_undo_redo_post),
    (bpy.app.handlers.redo_post, on_undo_redo_post),
    (bpy.app.handlers.depsgraph_update_post, on_depsgraph_update_post),
]


def register():
    for handler_list, handler_func in _handlers:
        handler_list.append(handler_func)
        log.debug(f"Registered handler '{handler_func.__name__}'")
    log.info("Registered msgbus update system.")


def unregister():
    if bpy.app.timers.is_registered(_deferred_update):
        bpy.app.timers.unregister(_deferred_update)

    try:
        bpy.msgbus.clear_by_owner(_msgbus_owner)
    except Exception:
        pass

    for handler_list, handler_func in _handlers:
        if handler_func in handler_list:
            handler_list.remove(handler_func)

    log.info("Unregistered msgbus update system.")
