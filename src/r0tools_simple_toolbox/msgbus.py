import logging

import bpy

from . import utils as u
from .operators import CustomTransformsOrientationsTracker
from .vertex_groups import vertex_groups_list_update

log = logging.getLogger(__name__)


# Global subscription owner - persists across blend file operations
_msgbus_owner = object()

# Debounce flags to prevent rapid successive updates
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

    log.debug("Subscribed to selection changes")


def _subscribe_to_object_vertex_groups(obj):
    """Subscribe to vertex group changes on specific object"""
    try:
        # Subscribe to collection
        bpy.msgbus.subscribe_rna(
            key=obj.path_resolve("vertex_groups", False),
            owner=_msgbus_owner,
            args=(obj,),
            notify=_on_vertex_groups_modified,
        )
    except Exception as e:
        log.warning(f"Unable to subscribe to vertex groups on {obj.name}: {e}")


def _on_selection_changed():
    """Selection changed callback"""
    log.debug("Selection changed - trigger update")

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

    _process_pending_updates()


def _on_vertex_groups_modified(obj):
    """Callback when vertex groups are added/removed/renamed on an object"""

    log.debug(f"Vertex groups modified on {obj.name}")

    if obj in u.get_selected_objects():
        _pending_updates["vertex_groups"] = True
        _process_pending_updates()


# ============================================================================
# Depsgraph Detection (Read-Only, Safe)
# ============================================================================


@bpy.app.handlers.persistent
def on_depsgraph_update_post(scene, depsgraph):
    # Early exits
    if u.is_saving():
        return

    if u.is_updating():
        return

    global _last_selection_hash
    current_hash = _compute_selection_hash()

    if current_hash != _last_selection_hash:
        log.debug(f"Selection changed (depsgraph fallback)")
        _last_selection_hash = current_hash

        # Re-subscribe to vertex groups for the new selections
        for obj in u.get_selected_objects():
            _subscribe_to_object_vertex_groups(obj)

        # Set flags
        _pending_updates["vertex_groups"] = True
        _pending_updates["properties"] = True
        _pending_updates["attributes"] = True
        _schedule_deferred_update()

    # Check object count changes (read-only and defer)
    if depsgraph.id_type_updated(u.DEPSGRAPH_ID_TYPES.OBJECT):
        if u.object_count_changed():
            log.debug(f"Object count changed via depsgraph")
            _pending_updates["objects"] = True
            _schedule_deferred_update()


def _compute_selection_hash():
    try:
        selected = tuple(sorted(obj.name for obj in u.get_selected_objects()))
        active_object = u.get_active_object()
        active_name = active_object.name if active_object else None
        return hash((selected, active_name))
    except:
        return None


# ============================================================================
# Update Processing
# ============================================================================


def _schedule_deferred_update():
    if not bpy.app.timers.is_registered(_deferred_update):
        bpy.app.timers.register(_deferred_update, first_interval=0.0)


def _deferred_update():
    """
    This is called via timer, not during depsgraph evaluation.
    """
    _process_pending_updates()
    return None  # Don't repeat


def _process_pending_updates():
    """
    Process all pending updates in one batch.
    This prevents multiple rapid callbacks from triggering redundant updates.
    """

    if u.is_saving():
        log.info("Skipping updates: File is saving")
        return

    if u.is_updating():
        log.info("Skipping updates: Update already in progress")
        return

    # Check any pending updates
    if not any(_pending_updates.values()):
        return

    scene = u.get_scene()

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
    log.debug("Undo/Redo post - re-establishing subscriptions")
    if u.object_count_changed():
        _pending_updates["properties"] = True
        _pending_updates["attributes"] = True
        _pending_updates["objects"] = True
        _schedule_deferred_update()

    subscribe_to_all_changes()


@bpy.app.handlers.persistent
def on_save_pre(dummy):
    """Clear pending updates before saving"""
    global _pending_updates
    _pending_updates = {key: False for key in _pending_updates}


_handlers = [
    (bpy.app.handlers.load_post, on_load_post),
    (bpy.app.handlers.undo_post, on_undo_redo_post),
    (bpy.app.handlers.redo_post, on_undo_redo_post),
    (bpy.app.handlers.save_pre, on_save_pre),
    (bpy.app.handlers.depsgraph_update_post, on_depsgraph_update_post),
]


def register():
    log.info("Register msgbus.")

    for handler_list, handler_func in _handlers:
        handler_list.append(handler_func)
        log.debug(f"Register '{handler_func.__name__}'")

    log.info("Msgbus handlers registered (subscriptions deferred to load_post).")


def unregister():
    # Clear all msgbus subscriptions
    try:
        bpy.msgbus.clear_by_owner(_msgbus_owner)
    except:
        pass  # May fail if Blender is shutting down

    for handler_list, handler_func in _handlers:
        if handler_func in handler_list:
            handler_list.remove(handler_func)

    log.info("Unregister msgbus.")
