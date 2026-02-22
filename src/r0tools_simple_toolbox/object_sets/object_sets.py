import logging
import time

import bmesh
import bpy

from .. import utils as u

log = logging.getLogger(__name__)

pending_known_objects: list[bpy.types.Object] = []


def get_object_sets(scene=None) -> list:
    addon_object_sets_props = u.get_addon_object_sets_props(scene=scene)

    return addon_object_sets_props.object_sets


def get_object_sets_count() -> int:
    return len(get_object_sets())


def get_active_object_set_index() -> int:
    addon_object_sets_props = u.get_addon_object_sets_props()
    active_index = addon_object_sets_props.object_sets_index

    return active_index


def set_active_object_set_index(index: int):
    addon_object_sets_props = u.get_addon_object_sets_props()

    if index < get_object_sets_count():
        addon_object_sets_props.object_sets_index = index


def get_object_set_at_index(index: int):
    object_sets = get_object_sets()

    if index < get_object_sets_count():
        return object_sets[index]

    return None


def remove_object_set_at_index(index: int):
    object_sets = get_object_sets()

    if index < get_object_sets_count():
        object_sets.remove(index)


def get_object_set_name_at_index(index: int) -> str:
    object_set = get_object_set_at_index(index)

    if not object_set:
        return ""

    return object_set.name


def set_object_set_name(object_set, new_name) -> bool:
    try:
        object_set.name = new_name
    except Exception as e:
        log.error(f"Unable to rename object set: {e}")
        return False

    return True


def set_object_set_name_at_index(index, new_name) -> bool:
    object_set = get_object_set_at_index(index)

    if object_set:
        object_set.name = new_name
        return True

    return False


def object_set_at_index_update_count(index: int) -> bool:
    object_set = get_object_set_at_index(index)

    if object_set:
        object_set.update_count()
        return True

    return False


def get_object_set_objects_at_index(index: int):
    object_set = get_object_set_at_index(index)

    if object_set:
        return object_set.objects

    return None


def iter_objects_of_object_set_at_index(index: int):
    object_set = get_object_set_at_index(index)

    if object_set:
        for obj_prop in object_set.objects:
            yield obj_prop.object

    return None


def move_object_set_to_index(from_index, to_index):
    object_sets = get_object_sets()

    object_sets.move(from_index, to_index)


def add_set_reference_to_obj(obj: bpy.types.Object, set_uuid: str):
    if not obj or not set_uuid:
        return

    object_props = u.get_object_props(obj)

    existing_uuids = {item.uuid for item in object_props.object_sets}
    if set_uuid not in existing_uuids:
        new_ref = object_props.object_sets.add()
        new_ref.uuid = set_uuid


def remove_set_reference_from_obj(obj: bpy.types.Object, set_uuid: str):
    if not obj or not set_uuid:
        return

    object_props = u.get_object_props(obj)

    for i, prop in reversed(list(enumerate(object_props.object_sets))):
        if object_props.object_sets[i].uuid == set_uuid:
            object_props.object_sets.remove(i)


def cleanup_object_set_invalid_references(scene=None):
    """Optimised cleanup using batch operations"""

    scene = u.get_scene(scene)

    addon_object_sets_props = u.get_addon_object_sets_props(scene=scene)

    # Build set of object names for O(1) lookup
    valid_objects = set(scene.objects.keys())
    total_cleaned = 0

    for object_set in addon_object_sets_props.object_sets:
        if object_set.separator:
            continue

        # Perf: fast pre-check if all members are valid, skip entirely
        if all(item.object is not None and item.object.name in valid_objects for item in object_set.objects):
            continue

        # Collect indices in one pass
        indices_to_remove = [
            i
            for i, item in enumerate(object_set.objects)
            if item.object is None or item.object.name not in valid_objects
        ]

        if not indices_to_remove:
            continue

        # Remove in reverse order
        cleaned_up = 0
        for i in reversed(indices_to_remove):
            try:
                object_set.objects.remove(i)
                cleaned_up += 1
            except Exception as e:
                log.error(f"Failed to remove object at index {i} of {object_set.name}: {e}")

        object_set.update_count()
        total_cleaned += len(indices_to_remove)
        log.info(f"Cleaned up {cleaned_up} references for Object Set '{object_set.name}'")

    if total_cleaned > 0:
        u.tag_redraw_if_visible()

    return None


def handle_object_duplication_update(scene=None):
    """
    Checks selected objects and assigns them to the correct Object Sets
    based on their stored UUIDs.

    This should be called from a depsgraph update handler when new objects
    are detected.
    """

    global pending_known_objects

    scene = u.get_scene(scene)

    log.debug(f"Handle Object Duplication Update")

    # Global list of object sets
    object_sets = u.get_object_sets(scene=scene)
    if not object_sets:
        return None

    # Process known identified changes first
    new_objects = pending_known_objects[:]
    _tag_redraw: bool = False if not new_objects else True
    pending_known_objects.clear()  # Consume staged changes
    log.debug(f"{new_objects=}")

    data_to_process = new_objects if new_objects else list(u.iter_scene_objects(selected=True))

    log.debug(f"{data_to_process=}")

    # Lookup dict for efficiency
    # Pre-prepare caches before iteration.
    # Should help with performance as it ensures _get_or_build_cache()
    # is a pure dict lookup on subsequent calls.
    uuid_to_set_map = {obj_set.uuid: obj_set for obj_set in object_sets if not obj_set.separator}
    for obj_set in uuid_to_set_map.values():
        obj_set._get_or_build_cache()

    bulk_assign: dict = {}

    for obj in data_to_process:
        object_props = u.get_object_props(obj)
        if not object_props or not hasattr(object_props, "object_sets"):
            continue

        member_uuids = {member.uuid for member in object_props.object_sets}

        for set_uuid in member_uuids:
            target_set = uuid_to_set_map.get(set_uuid)
            if not target_set:
                continue

            cache = target_set._get_or_build_cache()
            # Use cache for efficient lookup
            if obj.as_pointer() not in cache:
                # Object needs to be assigned. Schedule.
                bulk_assign.setdefault(target_set, []).append(obj)

    if not bulk_assign:
        return

    log.debug(f"Found {sum(len(v) for v in bulk_assign.values())} new assignments to process.")

    # Perform assignments only for objects that really need it
    for target_set, objects in bulk_assign.items():
        target_set.assign_objects(objects)

    if _tag_redraw:
        u.tag_redraw_if_visible()

    return None


def check_object_in_sets(obj, fast: bool = False) -> list:
    """
    Checks if an object is present in more Object Sets. If so
    return a list of references to each Object Set containing the object

    `fast`: Forces return of first instance found, avoiding checing all sets.

    :return: `list` of `Object Sets`
    """

    if not obj:
        return []

    containing_sets = []
    obj_ptr = obj.as_pointer()

    all_objects_sets = get_object_sets()

    for object_set in all_objects_sets:
        if object_set.separator:
            continue

        cache = object_set._get_or_build_cache()

        if obj_ptr in cache:
            containing_sets.append(object_set)
            if fast:
                break

    return containing_sets


_show_states_updated = False
_last_show_states = (False, False, False, False)
_mesh_stats_cache = {}
_last_update_time = 0


def object_sets_update_mesh_stats(depsgraph=None):
    log.info("------------- Object Sets Update Mesh Stats -------------")

    scene = bpy.context.scene

    addon_props = u.get_addon_props()
    addon_object_sets_props = u.get_addon_object_sets_props()

    if not addon_object_sets_props.experimental_features:
        return

    if not addon_object_sets_props.object_sets_modal:
        if not addon_props.cat_show_object_sets_editor:
            return

    show_verts = addon_object_sets_props.object_sets_show_mesh_verts
    show_edges = addon_object_sets_props.object_sets_show_mesh_edges
    show_faces = addon_object_sets_props.object_sets_show_mesh_faces
    show_tris = addon_object_sets_props.object_sets_show_mesh_tris

    global _show_states_updated, _last_show_states

    current_show_states = (show_verts, show_edges, show_faces, show_tris)
    _show_states_updated = current_show_states != _last_show_states
    _last_show_states = current_show_states

    if not any([show_verts, show_edges, show_faces, show_tris]):
        return

    # Filter depsgraph updates
    if depsgraph and not _should_update_stats(depsgraph):
        return

    _calculate_mesh_stats(show_verts, show_edges, show_faces, show_tris)


def _should_update_stats(depsgraph: bpy.types.Depsgraph):
    for update in depsgraph.updates:
        if update.is_updated_geometry:
            return True

        if update.is_updated_transform:
            obj = update.id
            if hasattr(obj, "type") and obj.type in {"MESH", "CURVE"}:
                # Only update if object might have become visible/hidden
                if not u.is_object_visible_in_viewport(obj):
                    continue
                return True

    return False


def _get_object_mesh_stats(obj, depsgraph, show_verts, show_edges, show_faces, show_tris):
    try:
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()

        if not mesh:
            return None

        stats = {}

        # Only calculate what's needed
        if show_verts:
            stats["verts"] = len(mesh.vertices)
        if show_edges:
            stats["edges"] = len(mesh.edges)
        if show_verts:
            stats["faces"] = len(mesh.polygons)

        # Triangle count
        if show_tris:
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                bmesh.ops.triangulate(bm, faces=bm.faces)
                stats["tris"] = len(bm.faces)
            finally:
                bm.free()

        return stats

    except Exception as e:
        log.error(f"Error processing {obj.name}: {e}")
        return None
    finally:
        if "mesh" in locals() and mesh:
            obj_eval.to_mesh_clear()


def _calculate_mesh_stats(show_verts, show_edges, show_faces, show_tris):
    # Get the evaluated version of the object (with modifiers applied)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    current_time = time.time()

    global _mesh_stats_cache, _last_update_time, _show_states_updated

    if current_time - _last_update_time > 5 or _show_states_updated:
        _mesh_stats_cache.clear()
        _last_update_time = current_time

    for object_set in u.get_object_sets():
        total_verts = 0
        total_edges = 0
        total_faces = 0
        total_tris = 0

        for obj_container in object_set.objects:
            obj = obj_container.object

            cache_key = obj

            # Use cached data if available
            if cache_key in _mesh_stats_cache:
                cached_stats = _mesh_stats_cache[cache_key]
                total_verts += cached_stats.get("verts", 0) if show_verts else 0
                total_edges += cached_stats.get("edges", 0) if show_edges else 0
                total_faces += cached_stats.get("faces", 0) if show_faces else 0
                total_tris += cached_stats.get("tris", 0) if show_tris else 0
                continue

            stats = _get_object_mesh_stats(obj, depsgraph, show_verts, show_edges, show_faces, show_tris)
            if stats:
                _mesh_stats_cache[cache_key] = stats
                total_verts += stats.get("verts", 0) if show_verts else 0
                total_edges += stats.get("edges", 0) if show_edges else 0
                total_faces += stats.get("faces", 0) if show_faces else 0
                total_tris += stats.get("tris", 0) if show_tris else 0

        # Update object set properties
        if show_verts:
            object_set.verts = total_verts
        if show_edges:
            object_set.edges = total_edges
        if show_faces:
            object_set.faces = total_faces
        if show_tris:
            object_set.tris = total_tris

    # Force UI Update to reflect changes
    """Only redraw UI areas that are actually visible and relevant."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            # Only redraw if area is visible and relevant
            if area.type == "PROPERTIES":
                # Check if object properties panel is active
                for space in area.spaces:
                    if hasattr(space, "context") and space.context == "OBJECT":
                        area.tag_redraw()
                        break
            elif area.type in {"OUTLINER", "VIEW_3D"}:
                area.tag_redraw()


@bpy.app.handlers.persistent
def refresh_object_sets_colours(context, force=False):
    """Refresh colors for all object sets"""

    log.debug(f"Force Refreshing Object Sets' Colours")

    addon_object_sets_props = u.get_addon_object_sets_props()
    allow_colour_override = addon_object_sets_props.object_sets_colour_allow_override

    # When allowing override, don't refresh the colours to any set colours
    if allow_colour_override and not force:
        log.info("Cancelling Object Sets' colour refresh as allowed colour override is in effect.")
        return

    object_sets = get_object_sets()

    if not addon_object_sets_props.object_sets_use_colour:
        return

    for object_set in object_sets:
        log.info(f"Refresh: {object_set.name}")
        object_set.update_object_set_colour(context)

    log.info(f"Finished refreshing Object Set's colours.")


@bpy.app.handlers.persistent
def load_legacy_object_sets(dummy):
    """Load legacy properties into new properties"""

    addon_props = u.get_addon_props()

    legacy_sets = addon_props.object_sets

    if legacy_sets:
        log.info(f"Loading legacy sets")

    # Collect objects
    total_objects = 0
    for legacy_set in legacy_sets:
        total_objects += len(legacy_set.objects)

    ### Progress Bar ###
    # TODO: Keep for now, might need to be removed later
    # if issues with segmentation fault start popping up
    wm = bpy.context.window_manager
    total_objects = total_objects
    total_processed = 0
    wm.progress_begin(0, total_objects)

    for legacy_set in legacy_sets:
        new_set = u.get_object_sets().add()
        if legacy_set.separator:
            new_set.separator = True
            new_set.name = new_set.default_separator_name
            log.info(f"Copy legacy Separator '{legacy_set.name}'")
            continue

        exists = legacy_set.name in [object_set.name for object_set in u.get_object_sets()]
        new_set.name = f"legacy_{legacy_set.name}" if exists else legacy_set.name
        new_set.set_colour = (
            legacy_set.set_colour
        )  # removed `set_object_set_colour` to prefer direct data to not trigger checks and updates.

        legacy_objects = legacy_set.objects

        log.info(f"Copying legacy Set '{legacy_set.name}' ({len(legacy_objects)} Objects)")

        for item in legacy_objects:
            legacy_obj = item.object

            # new.assign_objects(legacy_obj)
            # Prefer direct data assignment to prevent checks and updates
            new_obj = new_set.objects.add()
            new_obj.object = legacy_obj

            total_processed += 1
            wm.progress_update(total_processed)

        # Update count manually
        new_set.count = len(new_set.objects)

    wm.progress_end()

    # Remove legacy object sets
    if legacy_sets:
        log.info(f"Clearing legacy sets")
        if u.is_writing_context_safe(bpy.context.scene):
            legacy_sets.clear()
        else:
            log.error(f"Unable to clear legacy Object Sets")


def draw_objects_sets_uilist(layout, context):
    """
    Draw the Objects Sets UI list

    Args:
        layout: The layout to draw in
        context: The current context
        object_sets_box: Optional box to draw within
    """

    from ..menus import SimpleToolbox_MT_ObjectSetsActionsMenu
    from .operators import (
        SimpleToolbox_OT_AddObjectSetPopup,
        SimpleToolbox_OT_AddToObjectSet,
        SimpleToolbox_OT_MoveObjectSetItem,
        SimpleToolbox_OT_RandomiseObjectSetsColours,
        SimpleToolbox_OT_RemoveFromObjectSet,
        SimpleToolbox_OT_RemoveObjectSet,
    )

    addon_prefs = u.get_addon_prefs()
    addon_object_sets_props = u.get_addon_object_sets_props()

    _object_sets_use_colour = addon_object_sets_props.object_sets_use_colour

    # Experimental Features Checkbox
    row = layout.row()
    row.prop(addon_object_sets_props, "experimental_features")

    # Object Sets Row Number Slider
    row = layout.row()
    col_left = row.column()
    col_left.alignment = "LEFT"
    col_left.prop(addon_object_sets_props, "object_sets_list_rows", text="Rows:")
    col_right = row.column()
    col_right.separator()

    if addon_object_sets_props.experimental_features:
        # Object Sets Visual Aids
        row = layout.row()
        # Show mesh verts
        row.prop(addon_object_sets_props, "object_sets_show_mesh_verts", text="", icon="VERTEXSEL")
        # Show mesh edges
        row.prop(addon_object_sets_props, "object_sets_show_mesh_edges", text="", icon="EDGESEL")
        # Show mesh faces
        row.prop(addon_object_sets_props, "object_sets_show_mesh_faces", text="", icon="FACESEL")
        # Show mesh triangles
        row.prop(addon_object_sets_props, "object_sets_show_mesh_tris", text="", icon="MESH_DATA")

    row = layout.row()

    # Left Section - List
    col_left = row.column()
    col_left.template_list(
        "R0PROP_UL_ObjectSetsList",
        "object_sets",
        addon_object_sets_props,  # Collection owner
        "object_sets",  # Collection property
        addon_object_sets_props,  # Active item owner
        "object_sets_index",  # Active item property
        rows=addon_object_sets_props.object_sets_list_rows,
    )

    # Right side - Buttons
    col_right = row.column(align=True)
    col_right.alignment = "RIGHT"
    col_right.scale_x = addon_prefs.OPERATOR_COLUMN_SIZE_X
    col_right.operator(SimpleToolbox_OT_AddObjectSetPopup.bl_idname, text="+")
    col_right.operator(SimpleToolbox_OT_RemoveObjectSet.bl_idname, text="-")
    if len(addon_object_sets_props.object_sets) > 1:  # Show buttons only when applicable
        col_right.separator(factor=1.0)  # Spacer
        col_right.operator(SimpleToolbox_OT_MoveObjectSetItem.bl_idname, icon="TRIA_UP", text="").direction = "UP"
        col_right.operator(SimpleToolbox_OT_MoveObjectSetItem.bl_idname, icon="TRIA_DOWN", text="").direction = "DOWN"

    # Object Sets Use Colour
    col_right.separator(factor=1.0)  # Spacer
    if _object_sets_use_colour:
        col_right.prop(addon_object_sets_props, "object_sets_use_colour", text="", icon="RESTRICT_COLOR_ON")
    else:
        col_right.prop(addon_object_sets_props, "object_sets_use_colour", text="", icon="RESTRICT_COLOR_OFF")

    # Conditionally, only show the randomise object set colour button if we're using colours for object sets
    if _object_sets_use_colour:
        col_right.separator(factor=1.0)  # Spacer
        col_right.operator(SimpleToolbox_OT_RandomiseObjectSetsColours.bl_idname, text="", icon="NODE_MATERIAL")

    # Object Sets Actions (Downward arrow dropdown menu)
    col_right.separator(factor=1.0)  # Spacer
    col_right.menu(SimpleToolbox_MT_ObjectSetsActionsMenu.bl_idname, text="")

    row = layout.row(align=True)

    # Add/Remove Object Set Buttons
    split = row.split()  # Was factor=0.65
    row_col = split.row(align=True)
    row_col.operator(SimpleToolbox_OT_AddToObjectSet.bl_idname)
    row_col.operator(SimpleToolbox_OT_RemoveFromObjectSet.bl_idname)
