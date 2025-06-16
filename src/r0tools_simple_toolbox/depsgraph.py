import time

import bpy

from . import utils as u
from .operators import CustomTransformsOrientationsTracker

_mod = "DEPSGRAPH"

_last_timed_execution = 0

_very_frequent_update_interval = 5  # 5 seconds
_frequent_update_interval = 60  # 1 minute
_infrequent_update_interval = 300  # 5 minutes


def _set_last_timed_execution(set_to):
    global _last_timed_execution

    if set_to != _last_timed_execution:
        _last_timed_execution = set_to


@bpy.app.handlers.persistent
def handler_depsgraph_post_update(scene, depsgraph):
    """Handler that runs after depsgraph updates"""
    global _last_timed_execution

    # Check specifically for object deletions
    if depsgraph.id_type_updated(u.DEPSGRAPH_ID_TYPES.OBJECT):
        if not u.is_writing_context_safe(scene, check_addon_props=True):
            print(f"[INFO] [{_mod}] We avoided an addon lock crash.")
            return None

        # Store results once
        now = time.time()
        time_diff = now - _last_timed_execution
        _frequent_interval_passed = time_diff > _frequent_update_interval
        _infrequent_interval_passed = time_diff > _infrequent_update_interval

        if _infrequent_interval_passed:
            _set_last_timed_execution(now)
            print(f"[MONITOR] [{_mod}] Infrequent interval passed")
            u.cleanup_object_set_invalid_references(scene)

        if _frequent_interval_passed:
            _set_last_timed_execution(now)
            print(f"[MONITOR] [{_mod}] Frequent interval passed")
            u.object_sets_update_mesh_stats(scene)

        u.property_list_update(scene, bpy.context)
        u.vertex_groups_list_update(scene, bpy.context)
    CustomTransformsOrientationsTracker.track_custom_orientations(scene)


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
        print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)
