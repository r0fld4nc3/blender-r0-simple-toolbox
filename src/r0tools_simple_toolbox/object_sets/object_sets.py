import bmesh
import bpy

from .. import utils as u

_mod = "OBJECT_SETS"


def get_object_sets() -> list:
    addon_object_sets_props = u.get_addon_object_sets_props()

    return addon_object_sets_props.object_sets


def get_object_sets_count() -> int:
    return len(get_object_sets())


def get_active_object_set_index() -> int:
    addon_object_sets_props = u.get_addon_object_sets_props()
    active_index = addon_object_sets_props.object_sets_index

    return active_index


def set_active_object_set_index(index: int):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Set Active Object Set Index: Unsafe Context.")
        return None

    addon_object_sets_props = u.get_addon_object_sets_props()

    if index < get_object_sets_count():
        addon_object_sets_props.object_sets_index = index


def get_object_set_at_index(index: int):
    object_sets = get_object_sets()

    if index < get_object_sets_count():
        return object_sets[index]

    return None


def remove_object_set_at_index(index: int):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Remove Object Set At Index: Unsafe Context.")
        return None

    object_sets = get_object_sets()

    if index < get_object_sets_count():
        object_sets.remove(index)


def get_object_set_name_at_index(index: int) -> str:
    object_set = get_object_set_at_index(index)

    if not object_set:
        return ""

    return object_set.name


def set_object_set_name(object_set, new_name) -> bool:
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Set Object Set Name: Unsafe Context.")
        return None

    try:
        object_set.name = new_name
    except Exception as e:
        print(f"[ERROR] [{_mod}] Unable to rename object set: {e}")
        return False

    return True


def set_object_set_name_at_index(index, new_name) -> bool:
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Set Object Set Name At Index: Unsafe Context.")
        return None

    object_set = get_object_set_at_index(index)

    if object_set:
        object_set.name = new_name
        return True

    return False


def object_set_at_index_update_count(index: int) -> bool:
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets At Index Update Count: Unsafe Context.")
        return None

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
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Iter Objects of Object Set At Index: Unsafe Context.")
        return None

    object_set = get_object_set_at_index(index)

    if object_set:
        for obj_prop in object_set.objects:
            yield obj_prop.object

    return None


def move_object_set_to_index(from_index, to_index):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Move To Index: Unsafe Context.")
        return None

    object_sets = get_object_sets()

    object_sets.move(from_index, to_index)


def cleanup_object_set_invalid_references(scene):
    """
    Remove invalid object references from object sets

    This cleans up references to deleted objects to prevent errors.
    """
    if u.IS_DEBUG():
        print("------------- Cleanup Object Sets Invalid References -------------")

    if not u.is_writing_context_safe(scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Cleanup Invalid References: Unsafe Context.")
        return None

    addon_object_sets_props = u.get_addon_object_sets_props()

    if (
        not addon_object_sets_props.cat_show_object_sets_editor
        or not addon_object_sets_props.cat_show_object_sets_editor
    ):
        return False

    # Focus only on cleaning object sets without rebuilding scene_objects/data_objects
    for object_set in addon_object_sets_props.object_sets:
        # Identify invalid objects without modifying anything yet
        invalid_objects = []
        for i, object_item in enumerate(object_set.objects):
            obj = object_item.object
            if not obj or obj.name not in scene.objects:
                invalid_objects.append(obj)

        initial_count = len(object_set.objects)
        object_set.remove_objects(sorted(invalid_objects, reverse=True))
        cleaned_up = initial_count - len(object_set.objects)

        if cleaned_up:
            print(f"[INFO] [{_mod}] Cleaned up {cleaned_up} references for Object Set '{object_set.name}'")

    # Force UI Update to reflect changes
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                area.tag_redraw()


def cleanup_object_set_invalid_references_o1():
    """Optimised cleanup using batch operations"""

    scene = bpy.context.scene

    if not u.is_writing_context_safe(scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Cleanup Invalid References O1: Unsafe Context.")
        return None

    addon_props = u.get_addon_props()
    addon_object_sets_props = u.get_addon_object_sets_props()

    if not addon_props.cat_show_object_sets_editor or not addon_props.show_object_sets:
        return

    # Build set of object names for O(1) lookup
    valid_objects = set(scene.objects.keys())
    total_cleaned = 0

    for object_set in addon_object_sets_props.object_sets:
        if object_set.separator:
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
                print(f"[ERROR] [{_mod}] Failed to remove object at index {i} of {object_set.name}: {e}")

        object_set.update_count()
        total_cleaned += len(indices_to_remove)

        print(f"[INFO] [{_mod}] Cleaned up {cleaned_up} references for Object Set '{object_set.name}'")

    if total_cleaned > 0:
        for area in bpy.context.screen.areas:
            if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                area.tag_redraw()


def check_object_in_sets(obj) -> list:
    """
    Checks if an object is present in more Object Sets. If so
    return a list of references to each Object Set containing the object

    :return: `list` of `Object Sets`
    """

    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Check Object In Sets: Unsafe Context.")
        return None

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

    return containing_sets


def object_sets_update_mesh_stats():
    if u.IS_DEBUG():
        print("------------- Object Sets Update Mesh Stats -------------")

    scene = bpy.context.scene

    if not u.is_writing_context_safe(scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Update Mesh Stats: Unsafe Context.")
        return

    addon_props = u.get_addon_props()
    addon_object_sets_props = u.get_addon_object_sets_props()

    if not addon_props.cat_show_object_sets_editor or not addon_props.show_object_sets:
        return

    show_verts = addon_object_sets_props.object_sets_show_mesh_verts
    show_edges = addon_object_sets_props.object_sets_show_mesh_edges
    show_faces = addon_object_sets_props.object_sets_show_mesh_faces
    show_tris = addon_object_sets_props.object_sets_show_mesh_tris

    if not any([show_verts, show_edges, show_faces, show_tris]):
        return

    # Get the evaluated version of the object (with modifiers applied)
    depsgraph = bpy.context.evaluated_depsgraph_get()

    for object_set in u.get_object_sets():
        total_verts = 0
        total_edges = 0
        total_faces = 0
        total_tris = 0

        # Cache mesh stats
        mesh_stats_cache = {}

        for obj_container in object_set.objects:
            obj = obj_container.object

            if not u.is_object_visible_in_viewport(obj):
                continue

            if obj.type not in [u.OBJECT_TYPES.MESH, u.OBJECT_TYPES.CURVE]:
                continue

            # Get the evaluated version of the object with modifiers applied
            obj_eval = obj.evaluated_get(depsgraph)

            # Create unique key for object's mesh state
            # Must account for object data and modifier stack
            mesh_key = (obj.data.name_full, tuple(mod.name for mod in obj.modifiers if mod.show_viewport))

            # Check if mesh is cached
            if mesh_key in mesh_stats_cache:
                cached_stats = mesh_stats_cache.get(mesh_key, "")
                if show_verts:
                    total_verts += cached_stats["verts"]
                if show_edges:
                    total_edges += cached_stats["edges"]
                if show_faces:
                    total_faces += cached_stats["faces"]
                if show_tris:
                    total_tris += cached_stats["tris"]
                continue

            # Process if not cached

            to_mesh = None
            try:
                to_mesh = obj_eval.to_mesh()

                stats = {
                    "verts": len(to_mesh.vertices) if show_verts else 0,
                    "edges": len(to_mesh.edges) if show_edges else 0,
                    "faces": len(to_mesh.polygons) if show_faces else 0,
                    "tris": 0,
                }

                if show_tris:
                    stats["tris"] = sum(len(poly.vertices) - 2 for poly in to_mesh.polygons)

                # Cache the stats
                mesh_stats_cache[mesh_key] = stats

                # Add to totals
                if show_verts:
                    total_verts += stats["verts"]
                if show_edges:
                    total_edges += stats["edges"]
                if show_faces:
                    total_faces += stats["faces"]
                if show_tris:
                    total_tris += stats["tris"]
            except Exception as e:
                print(f"[ERROR] [{_mod}] Error processing {obj.name}: {e}")
            finally:
                # Always cleanup temporary mesh
                if to_mesh or to_mesh is not None:
                    obj_eval.to_mesh_clear()

        # Update all stats
        if show_verts:
            object_set.verts = total_verts
        if show_edges:
            object_set.edges = total_edges
        if show_faces:
            object_set.faces = total_faces
        if show_tris:
            object_set.tris = total_tris

    # Force UI Update to reflect changes
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                area.tag_redraw()


@bpy.app.handlers.persistent
def refresh_object_sets_colours(context):
    """Refresh colors for all object sets"""

    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Refresh Object Sets Colours: Unsafe Context.")
        return None

    if u.IS_DEBUG():
        print(f"[DEBUG] [{_mod}] Force Refreshing Object Sets' Colours")

    addon_prefs = u.get_addon_prefs()

    object_sets = get_object_sets()

    if not addon_prefs.object_sets_use_colour:
        return

    for object_set in object_sets:
        if u.IS_DEBUG():
            print(f"[DEBUG] [{_mod}] Refresh: {object_set.name}")
        object_set.update_object_set_colour(context)


@bpy.app.handlers.persistent
def load_legacy_object_sets(dummy):
    """Load legacy properties into new properties"""

    addon_props = u.get_addon_props()

    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[ERROR] [{_mod}] Context write is not safe")
        return

    legacy_sets = addon_props.object_sets

    if legacy_sets:
        print(f"[INFO] [{_mod}] Loading legacy sets")

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
            print(f"[INFO] [{_mod}] Copy legacy Separator '{legacy_set.name}'")
            continue

        exists = legacy_set.name in [object_set.name for object_set in u.get_object_sets()]
        new_set.name = f"legacy_{legacy_set.name}" if exists else legacy_set.name
        new_set.set_colour = (
            legacy_set.set_colour
        )  # removed `set_object_set_colour` to prefer direct data to not trigger checks and updates.

        legacy_objects = legacy_set.objects

        print(f"[INFO] [{_mod}] Copying legacy Set '{legacy_set.name}' ({len(legacy_objects)} Objects)")

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
        print(f"[INFO] [{_mod}] Clearing legacy sets")
        if u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
            legacy_sets.clear()
        else:
            print(f"[ERROR] [{_mod}] Unable to clear legacy Object Sets")


def draw_objects_sets_uilist(layout, context, object_sets_box=None):
    """
    Draw the Objects Sets UI list

    Args:
        layout: The layout to draw in
        context: The current context
        object_sets_box: Optional box to draw within
    """

    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Object Sets Draw Object Sets UIList: Unsafe Context.")
        return None

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

    _object_sets_use_colour = addon_prefs.object_sets_use_colour

    # Object Sets Editor parent layout
    if object_sets_box:
        parent = object_sets_box
    elif layout:
        parent = layout
    else:
        print(f"[ERROR] [{_mod}] No valid layout to use:\n{layout=}\n{object_sets_box=}")
        return False

    # Object Sets Row Number Slider
    row = parent.row()
    split = row.split(factor=0.35)
    col = split.column()
    col.prop(addon_prefs, "object_sets_list_rows", text="Rows:")
    col = split.column()
    col.separator()

    # Object Sets Visual Aids
    row = parent.row()
    # Show mesh verts
    row.prop(addon_object_sets_props, "object_sets_show_mesh_verts", text="", icon="VERTEXSEL")
    # Show mesh edges
    row.prop(addon_object_sets_props, "object_sets_show_mesh_edges", text="", icon="EDGESEL")
    # Show mesh faces
    row.prop(addon_object_sets_props, "object_sets_show_mesh_faces", text="", icon="FACESEL")
    # Show mesh triangles
    row.prop(addon_object_sets_props, "object_sets_show_mesh_tris", text="", icon="MESH_DATA")

    row = parent.row()
    split = row.split(factor=0.92)  # Affects right side button width

    # Left Section - List
    col = split.column()
    col.template_list(
        "R0PROP_UL_ObjectSetsList",
        "object_sets",
        addon_object_sets_props,  # Collection owner
        "object_sets",  # Collection property
        addon_object_sets_props,  # Active item owner
        "object_sets_index",  # Active item property
        rows=addon_prefs.object_sets_list_rows,
    )

    # Right side - Buttons
    col = split.column(align=True)
    col.operator(SimpleToolbox_OT_AddObjectSetPopup.bl_idname, text="+")
    col.operator(SimpleToolbox_OT_RemoveObjectSet.bl_idname, text="-")
    if len(addon_object_sets_props.object_sets) > 1:  # Show buttons only when applicable
        col.separator(factor=1.0)  # Spacer
        col.operator(SimpleToolbox_OT_MoveObjectSetItem.bl_idname, icon="TRIA_UP", text="").direction = "UP"
        col.operator(SimpleToolbox_OT_MoveObjectSetItem.bl_idname, icon="TRIA_DOWN", text="").direction = "DOWN"

    # Object Sets Use Colour
    col.separator(factor=1.0)  # Spacer
    if _object_sets_use_colour:
        col.prop(addon_prefs, "object_sets_use_colour", text="", icon="RESTRICT_COLOR_ON")
    else:
        col.prop(addon_prefs, "object_sets_use_colour", text="", icon="RESTRICT_COLOR_OFF")

    # Conditionally, only show the randomise object set colour button if we're using colours for object sets
    if _object_sets_use_colour:
        col.separator(factor=1.0)  # Spacer
        col.operator(SimpleToolbox_OT_RandomiseObjectSetsColours.bl_idname, text="", icon="NODE_MATERIAL")

    # Object Sets Actions (Downward arrow dropdown menu)
    col.separator(factor=1.0)  # Spacer
    col.menu(SimpleToolbox_MT_ObjectSetsActionsMenu.bl_idname, text="")

    # Bottom
    if object_sets_box:
        parent = object_sets_box
    else:
        parent = layout
    row = parent.row(align=True)

    # Add/Remove Object Set Buttons
    split = row.split()  # Was factor=0.65
    row_col = split.row(align=True)
    row_col.operator(SimpleToolbox_OT_AddToObjectSet.bl_idname)
    row_col.operator(SimpleToolbox_OT_RemoveFromObjectSet.bl_idname)
