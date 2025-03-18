import queue

import bpy

from .constants import _ADDON_IN_ERROR_STATE, _QUEUE_RETRY_SECONDS

_operation_queue = queue.Queue()
_failed_operations = set()
_loops_with_failed_operations = 0


def is_safe_context_for_id_writes():
    """Check if the current context allows writing to ID properties"""
    try:
        # Test by writing to a temporary property
        temp_prop_name = "_temp_context_test"
        scene = bpy.context.scene

        # If the property already exists, we don't need to test
        if temp_prop_name in scene:
            return True

        # Try to set a temporary property
        scene[temp_prop_name] = True
        # If we got here, it worked!
        del scene[temp_prop_name]
        return True
    except Exception:
        # If we get an exception, it's not safe
        return False


def process_queue_ops():
    """
    Process operations from the queue in the main thread

    This runs operations in a safe context and handles errors
    without blocking Blender's UI.
    """
    from .general import IS_DEBUG

    global _failed_operations, _loops_with_failed_operations, _ADDON_IN_ERROR_STATE

    try:
        operations_processed = 0
        max_operations_per_frame = 100

        # Check if we're in a safe context for ID writes
        context_safe = is_safe_context_for_id_writes()

        while not _operation_queue.empty() and operations_processed < max_operations_per_frame:

            # Get the next operation
            operation = _operation_queue.get_nowait()

            # Skip operations that have failed too many times
            op_id = id(operation)
            if op_id in _failed_operations:
                _operation_queue.task_done()
                if IS_DEBUG():
                    print(f"[DEBUG] Skipping previously failed operation: {operation}")
                continue

            if IS_DEBUG():
                print(f"[DEBUG] Got Op: {operation}")

            try:
                # Only run the operation if we're in a safe context
                if context_safe:
                    operation()
                    # If successful, remove from failed operations if it was there
                    if op_id in _failed_operations:
                        _failed_operations.remove(op_id)
                else:
                    # Re-queue for later when context is safe
                    _operation_queue.put(operation)
                    if IS_DEBUG():
                        print(f"[DEBUG] Re-queued operation for later: {operation}")

                operations_processed += 1

            except Exception as e:
                print(f"[ERROR] Failed to execute queued operation: {e}")
                _failed_operations.add(op_id)
                _ADDON_IN_ERROR_STATE = True

                if IS_DEBUG():
                    print(f"[DEBUG] Processed: {operations_processed}")
                    print(f"[DEBUG] Queue size: {_operation_queue.qsize()}")
            finally:
                _operation_queue.task_done()
                if IS_DEBUG():
                    print(f"[DEBUG] Done: {operation}")

        # Clear old failed operations every few minutes to allow retrying
        if len(_failed_operations) > 0:
            if _loops_with_failed_operations > 5:
                _failed_operations.clear()
                _loops_with_failed_operations = 0  # Reset loop counter
                if IS_DEBUG():
                    print("[DEBUG] Cleared failed operations list")
            else:
                _loops_with_failed_operations += 1

        if not _operation_queue.empty():
            return 0.01  # Re-run soon if queue has items

        # If we're in an error state but the queue is empty, try recovery
        if _ADDON_IN_ERROR_STATE:
            return 0.5  # Schedule recovery

        return _QUEUE_RETRY_SECONDS

    except Exception as e:
        print(f"[ERROR] Error in process_queue_ops: {e}")
        return _QUEUE_RETRY_SECONDS


def queue_op(operation, *args, **kwargs):
    """
    Queue an operation to be executed in the main thread

    Args:
        operation: The function to queue
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    """
    if args or kwargs:
        _operation_queue.put(lambda: operation(*args, **kwargs))
    else:
        _operation_queue.put(operation)


def recover_from_error_state():
    """
    Attempt to recover from an error state

    Tries to restore normal operation after errors by clearing
    the failed operations list and error state flag.
    """
    global _ADDON_IN_ERROR_STATE, _failed_operations

    if not _ADDON_IN_ERROR_STATE:
        return _QUEUE_RETRY_SECONDS

    print("[UTILS] [RECOVERY] Attempting to recover from error state...")

    # Check if we're in a safe context before attempting recovery
    if not is_safe_context_for_id_writes():
        print("[UTILS] [RECOVERY] Context not safe for recovery, will try again later")
        return 0.5  # Try again soon

    _failed_operations.clear()

    # Reset error state
    _ADDON_IN_ERROR_STATE = False

    print("[UTILS] [RECOVERY] Error state cleared")

    # Force UI update
    for area in bpy.context.screen.areas:
        area.tag_redraw()

    return _QUEUE_RETRY_SECONDS


def timer_update_data_scene_objects():
    """Timer compatible wrapper for update_data_scene_objects"""
    from .tracking import update_data_scene_objects

    scene = bpy.context.scene
    queue_op(update_data_scene_objects, scene)
    return _QUEUE_RETRY_SECONDS


@bpy.app.handlers.persistent
def handler_update_data_scene_objects(scene):
    """Queue the update_data_scene_objects operation"""
    from .tracking import update_data_scene_objects

    queue_op(update_data_scene_objects, scene)


@bpy.app.handlers.persistent
def timer_continuous_property_list_update():
    """Timer wrapper for continuous_property_list_update"""
    from .tracking import continuous_property_list_update

    scene = bpy.context.scene
    ctx = bpy.context
    queue_op(continuous_property_list_update, scene, ctx)
    return _QUEUE_RETRY_SECONDS


@bpy.app.handlers.persistent
def handler_continuous_property_list_update(scene, context=None):
    """Queue the continuous_property_list_update operation"""
    from .tracking import continuous_property_list_update

    ctx = context or bpy.context
    queue_op(continuous_property_list_update, scene, ctx)


def timer_cleanup_object_set_invalid_references():
    """Timer wrapper for cleanup_object_set_invalid_references"""
    from .tracking import cleanup_object_set_invalid_references

    scene = bpy.context.scene
    queue_op(cleanup_object_set_invalid_references, scene)
    # Run cleanup more frequently than other operations
    return _QUEUE_RETRY_SECONDS / 2 if _QUEUE_RETRY_SECONDS >= 1 else _QUEUE_RETRY_SECONDS


@bpy.app.handlers.persistent
def handler_cleanup_object_set_invalid_references(scene):
    from .tracking import cleanup_object_set_invalid_references

    """Queue the cleanup_object_set_invalid_references operation"""
    queue_op(cleanup_object_set_invalid_references, scene)


@bpy.app.handlers.persistent
def handler_on_load_refresh_object_sets_colours(dummy):
    from .object_sets import refresh_object_sets_colours

    """Queue the refresh_object_sets_colours operation"""
    queue_op(refresh_object_sets_colours, bpy.context)


def register():
    if not bpy.app.timers.is_registered(process_queue_ops):
        print("[UTILS] Register timer: process_queue_ops")
        bpy.app.timers.register(process_queue_ops, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(process_queue_ops):
        print("[UTILS] Register timer: process_queue_ops")
        bpy.app.timers.unregister(process_queue_ops)
