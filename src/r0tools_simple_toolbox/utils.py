import math
import queue
import random
from pathlib import Path

import bpy

from .const import DEBUG, INTERNAL_NAME

# Global state variables
_ADDON_IN_ERROR_STATE = False
_QUEUE_RETRY_SECONDS = 0.5  # Default retry interval
_operation_queue = queue.Queue()
_failed_operations = set()
_loops_with_failed_operations = 0

# ==============================
# CONSTANT DEFINITIONS
# ==============================

# fmt: off
class CUSTOM_PROPERTIES_TYPES:
    OBJECT_DATA = "OBJECT DATA"
    MESH_DATA   = "MESH DATA"


class OBJECT_MODES:
    OBJECT        = "OBJECT"
    OBJECT_MODE   = "OBJECT_MODE"
    EDIT          = "EDIT"
    EDIT_MODE     = "EDIT_MODE"
    EDIT_MESH     = "EDIT_MESH"
    SCULPT        = "SCULPT"
    VERTEX_PAINT  = "VERTEX_PAINT"
    TEXTURE_PAINT = "TEXTURE_PAINT"
    WEIGHT_PAINT  = "WEIGHT_PAINT"


class OBJECT_TYPES:
    MESH         = "MESH"
    CURVE        = "CURVE"
    SURFACE      = "SURFACE"
    META         = "META"
    FONT         = "FONT"
    CURVES       = "CURVES"
    POINTCLOUD   = "POINTCLOUD"
    VOLUME       = "VOLUME"
    GPENCIL      = "GPENCIL"
    GREASEPENCIL = "GREASEPENCIL"
    ARMATURE     = "ARMATURE"
    LATTICE      = "LATTICE"
    EMPTY        = "EMPTY"
    LIGHT        = "LIGHT"
    LIGHT_PROBE  = "LIGHT_PROBE"
    CAMERA       = "CAMERA"
    SPEAKER      = "SPEAKER"


class AREA_TYPES:
    CLIP_EDITOR      = "CLIP_EDITOR"
    CONSOLE          = "CONSOLE"
    DOPESHEET_EDITOR = "DOPESHEET_EDITOR"
    FILE_BROWSER     = "FILE_BROWSER"
    GRAPH_EDITOR     = "GRAPH_EDITOR"
    IMAGE_EDITOR     = "IMAGE_EDITOR"
    INFO             = "INFO"
    NLA_EDITOR       = "NLA_EDITOR"
    NODE_EDITOR      = "NODE_EDITOR"
    OUTLINER         = "OUTLINER"
    PREFERENCES      = "PREFERENCES"
    PROPERTIES       = "PROPERTIES"
    SEQUENCE_EDITOR  = "SEQUENCE_EDITOR"
    SPREADSHEET      = "SPREADSHEET"
    TEXT_EDITOR      = "TEXT_EDITOR"
    TOPBAR           = "TOPBAR"
    VIEW_3D          = "VIEW_3D"
# fmt: on


# ==============================
# CONTEXT & PROPERTY ACCESS
# ==============================
def IS_DEBUG():
    """Return current debug state"""
    addon_prefs = get_addon_prefs()
    return DEBUG or addon_prefs.debug


def get_scene() -> bpy.types.Scene:
    """Get the current scene"""
    return bpy.context.scene


def get_scene_name() -> str:
    """Get the name of the current scene"""
    return get_scene().name


def get_context_area() -> str | None:
    """Get the current area type or None if unavailable"""
    if not bpy.context.area:
        return None
    return bpy.context.area.ui_type


def get_addon_props():
    """Get the addon property group from current scene"""
    return get_scene().r0fl_toolbox_props


def get_addon_prefs():
    """Get the addon preferences"""
    return bpy.context.preferences.addons[INTERNAL_NAME].preferences


def get_addon_fs_path() -> Path:
    """Get the filesystem path to the addon directory from THIS file"""
    return Path(__file__).resolve().parent.parent


def get_depsgraph():
    """Get the current dependency graph"""
    return bpy.context.evaluated_depsgraph_get()


def get_depsgraph_is_updated_geometry() -> bool:
    """Check if geometry was updated in the depsgraph"""
    d = get_depsgraph()
    for update in d.updates:
        return update.is_updated_geometry
    return False


def get_depsgraph_is_updated_shading() -> bool:
    """Check if shading was updated in the depsgraph"""
    d = get_depsgraph()
    for update in d.updates:
        return update.is_updated_shading
    return False


def get_depsgraph_is_updated_transform() -> bool:
    """Check if transforms were updated in the depsgraph"""
    d = get_depsgraph()
    for update in d.updates:
        return update.is_updated_transform
    return False


def get_uvmap_size_x():
    """Get selected UV Map Size in X"""
    addon_props = get_addon_props()
    return int(addon_props.uv_size_x)


def get_uvmap_size_y():
    """Get selected UV Map Size in Y"""
    addon_props = get_addon_props()
    return int(addon_props.uv_size_y)


def save_preferences():
    """Safely save user preferences without causing recursion"""
    try:
        if not hasattr(save_preferences, "is_saving"):
            save_preferences.is_saving = False

        if not save_preferences.is_saving:
            save_preferences.is_saving = True
            bpy.context.preferences.use_preferences_save = True
            bpy.ops.wm.save_userpref()
            save_preferences.is_saving = False
    except Exception as e:
        print(f"Error saving preferences: {e}")
        save_preferences.is_saving = False


# ==============================
# OBJECT MANIPULATION
# ==============================


def set_object_mode(mode: str):
    """
    Set the current object mode

    - OBJECT
    - EDIT (EDIT_MESH)
    - SCULPT
    - VERTEX_PAINT
    - TEXTURE_PAINT
    - WEIGHT_PAINT

    Args:
        mode: One of the modes defined in `OBJECT_MODES`
    """
    if IS_DEBUG():
        print(f"Setting mode: {mode}")

    # Edit Mode weirdness fix
    if mode.upper() == "EDIT_MESH":
        mode = OBJECT_MODES.EDIT
    bpy.ops.object.mode_set(mode=mode)


def set_mode_object():
    """Sets the current mode to Object Mode"""
    set_object_mode("OBJECT")


def set_mode_edit():
    """Sets the current mode to Edit Mode"""
    set_object_mode("EDIT")


def select_object(obj: bpy.types.Object, add=True, set_active=False) -> bpy.types.Object | None:
    """
    Select an object in the scene

    Args:
        obj: Object to select
        add: Whether to add to current selection or replace it
        set_active: Whether to set this as the active object

    Returns:
        The selected object or None if failed
    """
    if IS_DEBUG():
        print(f"Selecting {obj.name} {add=} {set_active=}")
    if not add:
        deselect_all()

    if not is_valid_object_global(obj):
        return None

    try:
        obj.select_set(True)
    except Exception as e:
        print(f"[ERROR] Selecting {obj.name} {e}")

    if not add or set_active:
        set_active_object(obj)

    return obj


def deselect_object(obj: bpy.types.Object) -> bpy.types.Object | None:
    """
    Deselect an object in the scene

    Args:
        obj: Object to deselect

    Returns:
        The deselected object or None if failed
    """
    if IS_DEBUG():
        print(f"Deselecting {obj.name}")

    if not is_valid_object_global(obj):
        return None

    try:
        obj.select_set(False)
    except Exception as e:
        print(f"[ERROR] Deselecting {obj.name} {e}")

    return obj


def set_active_object(obj: bpy.types.Object):
    """Set the active object in the current view layer"""
    bpy.context.view_layer.objects.active = obj


def get_active_object() -> bpy.types.Object | None:
    """Get the active object from the current view layer"""
    return bpy.context.view_layer.objects.active


def is_object_visible_in_viewport(obj):
    """
    Check if an object is visible in the viewport

    This checks both the object's visibility setting and
    whether its collections are visible
    """
    # Check if the object is set to be visible in the viewport
    if not obj.visible_get():
        if IS_DEBUG():
            print(f"[DEBUG] {obj.name} is not visible in viewport.")
        return False

    if IS_DEBUG():
        print(f"[DEBUG] {obj.name} is visible in viewport.")
        print(f"[DEBUG] Checking {obj.name} Collection(s).")

    # Check if the object's collection is visible in the viewport
    for collection in obj.users_collection:
        if IS_DEBUG():
            print(f"[DEBUG]    - {collection.name}")
        if not collection.hide_viewport:
            if IS_DEBUG():
                print(f"[DEBUG]    - {collection.name} is visible.")
            return True
        else:
            if IS_DEBUG():
                print(f"[DEBUG]    - {collection.name} is hidden.")

    return False


def deselect_all():
    """Deselect all objects or elements based on current mode"""
    context_mode = bpy.context.mode
    edit_modes = [OBJECT_MODES.EDIT, OBJECT_MODES.EDIT_MODE]
    object_modes = [OBJECT_MODES.OBJECT, OBJECT_MODES.OBJECT_MODE]

    if context_mode in edit_modes:
        bpy.ops.mesh.select_all(action="DESELECT")
    elif context_mode in object_modes:
        bpy.ops.object.select_all(action="DESELECT")


def object_in_view_layer(obj, context=None):
    """Check if object is in the active view layer"""
    ctx = bpy.context
    if context:
        ctx = context

    return obj.visible_get(view_layer=ctx.view_layer)


def object_visible(obj):
    """Check if object is visible"""
    return obj.visible_get()


def is_valid_object_global(obj):
    """
    Check if an object reference is valid

    This detects dangling references to deleted objects
    """
    try:
        exists_mesh = (
            obj is not None
            and obj
            and obj.name in bpy.data.objects
            and any(obj.name in scene.objects for scene in bpy.data.scenes)
        )

        if not exists_mesh:
            if obj is not None:
                print(f"Dangling reference: {obj.name}")
            else:
                print(f"Dangling reference: {obj}")
            return False

        return True
    except ReferenceError:
        print(f"ReferenceError when checking object validity")
        return False
    except Exception as e:
        print(f"Error checking object validity: {e}")
        return False


def iter_scene_objects(selected=False, types: list[str] = []):
    """
    Iterate through objects in the scene

    Args:
        selected: Only iterate through selected objects
        types: Filter by object types (empty list = all types)
    """
    iters = bpy.data.objects
    if selected:
        iters = bpy.context.selected_objects

    for o in iters:
        if not types or o.type in types:
            yield o


def iter_children(p_obj, recursive=True):
    """
    Iterate through all children of a given parent object

    Args:
        p_obj: Parent object to find children for
        recursive: If True, also iterate through children of children
    """
    for obj in bpy.data.objects:
        if obj.parent == p_obj:
            yield obj
            if recursive:
                yield from iter_children(obj, recursive=True)


# ==============================
# MESH SELECTION MODE
# ==============================


def _set_mesh_selection_mode(use_extend=False, use_expand=False, type=""):
    """Base function for setting mesh selection mode"""
    bpy.ops.mesh.select_mode(use_extend=use_extend, use_expand=use_expand, type=type)


def set_mesh_selection_vertex(*args, **kwargs):
    """Set selection mode to Vertex"""
    kwargs["type"] = "VERT"
    _set_mesh_selection_mode(*args, **kwargs)


def set_mesh_selection_edge(*args, **kwargs):
    """Set selection mode to Edge"""
    kwargs["type"] = "EDGE"
    _set_mesh_selection_mode(*args, **kwargs)


def set_mesh_selection_face(*args, **kwargs):
    """Set selection mode to Face"""
    kwargs["type"] = "FACE"
    _set_mesh_selection_mode(*args, **kwargs)


# ==============================
# TRANSFORM ORIENTATIONS
# ==============================


def get_builtin_transform_orientations(identifiers=False) -> list:
    """
    Get list of built-in transform orientations

    Args:
        identifiers: Return identifiers instead of names
    """
    if identifiers:
        _ret = [i.identifier for i in bpy.types.TransformOrientationSlot.bl_rna.properties["type"].enum_items]
    else:
        _ret = [i.name for i in bpy.types.TransformOrientationSlot.bl_rna.properties["type"].enum_items]

    return _ret


def get_transform_orientations() -> list:
    """
    Returns a list of all transform orientation names

    Uses a workaround to get the names by intentionally
    causing an error with an empty string.
    """
    try:
        # This intentionally raises an exception to get valid values
        get_scene().transform_orientation_slots[0].type = ""
    except Exception as inst:
        transforms = str(inst).split("'")[1::2]

    transform_list = list(transforms)
    if IS_DEBUG():
        print(f"[DEBUG] {transform_list=}")

    return transform_list


def get_custom_transform_orientations() -> list:
    """Returns a list of custom transform orientation names"""
    custom_transforms = get_transform_orientations()[7:]  # The 7 first orientations are built-ins
    if IS_DEBUG():
        print(f"[DEBUG] {custom_transforms=}")

    return custom_transforms


def delete_custom_transform_orientation(name: str):
    """Delete a custom transform orientation by name"""
    transform_list = get_custom_transform_orientations()
    for enum_type in transform_list:
        if IS_DEBUG():
            print(f"[DEBUG] {enum_type=} == {name=}")
        if enum_type == name or str(enum_type).lower() == str(name).lower():
            get_scene().transform_orientation_slots[0].type = enum_type
            bpy.ops.transform.delete_orientation()


# ==============================
# UI & NOTIFICATIONS
# ==============================


def show_notification(message, title="Operation Complete"):
    """Display a popup notification and status info message"""
    bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text=message), title=title)
    bpy.context.workspace.status_text_set(message)


def force_redraw_all():
    """Force a redraw of all UI areas"""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def draw_objects_sets_uilist(layout, context, object_sets_box=None):
    """
    Draw the Objects Sets UI list

    Args:
        layout: The layout to draw in
        context: The current context
        object_sets_box: Optional box to draw within
    """
    addon_prefs = get_addon_prefs()
    addon_props = get_addon_props()

    # Object Sets Editor parent layout
    if object_sets_box:
        parent = object_sets_box
    elif layout:
        parent = layout
    else:
        print(f"[ERROR] No valid layout to use:\n{layout=}\n{object_sets_box=}")
        return False

    # Object Sets Use Colour
    row = parent.row()
    row.prop(addon_prefs, "object_sets_use_colour")

    # Object Sets Row Number Slider (Same as in addon preferences)
    row = parent.row()
    row.prop(addon_prefs, "object_sets_list_rows", text="Rows:")

    row = parent.row()
    split = row.split(factor=0.92)  # Affects right side button width

    # Left Section - List
    col = split.column()
    col.template_list(
        "R0PROP_UL_ObjectSetsList",
        "object_sets",
        addon_props,  # Collection owner
        "object_sets",  # Collection property
        addon_props,  # Active item owner
        "object_sets_index",  # Active item property
        rows=addon_prefs.object_sets_list_rows,
    )

    # Right side - Buttons
    col = split.column(align=True)
    col.operator("r0tools.add_object_set_popup", text="+")
    col.operator("r0tools.remove_object_set", text="-")
    if len(addon_props.object_sets) > 1:  # Show buttons only when applicable
        col.separator(factor=1.0)  # Spacer
        col.operator("r0tools.move_object_set_item_up", icon="TRIA_UP", text="")
        col.operator("r0tools.move_object_set_item_down", icon="TRIA_DOWN", text="")

    col.separator(factor=1.0)  # Spacer
    col.operator("r0tools.object_sets_refresh", text="", icon="FILE_REFRESH")

    col.separator(factor=1.0)  # Spacer
    col.operator("r0tools.object_sets_colours_randomise", text="", icon="NODE_MATERIAL")

    # Bottom
    if object_sets_box:
        parent = object_sets_box
    else:
        parent = layout
    row = parent.row(align=True)

    # Add/Remove Object Set Buttons
    split = row.split(factor=0.65)
    row_col = split.row(align=True)
    row_col.operator("r0tools.assign_to_object_set")
    row_col.operator("r0tools.remove_from_object_set")
    # Select Object Set Button
    row_col = split.row()
    op = row_col.operator("r0tools.select_object_set")
    op.set_index = -1


# ==============================
# OBJECT SETS & CUSTOM PROPERTIES
# ==============================


def refresh_object_sets_colours(context):
    """Refresh colors for all object sets"""
    print("[INFO] Force Refreshing Object Sets")
    addon_prefs = get_addon_prefs()
    addon_props = get_addon_props()
    object_sets = addon_props.object_sets

    if not addon_prefs.object_sets_use_colour:
        return

    for object_set in object_sets:
        if IS_DEBUG():
            print(f"[DEBUG] Refresh: {object_set.name}")
        queue_op(object_set.update_object_set_colour, context)


def continuous_property_list_update(scene, context, force_run=False):
    """
    Update property list based on selected objects

    This function updates the custom property list panel
    when object selection changes.
    """
    addon_props = get_addon_props()

    if not addon_props.show_custom_property_list_prop and not force_run:
        # Skip update if panel is not visible
        if IS_DEBUG():
            print(
                f"[DEBUG] Custom Properties Panel is not visible, exiting from running continuous property list update."
            )
        return None

    if bpy.context.selected_objects or force_run:
        current_selection = {obj.name for obj in iter_scene_objects(selected=True)}
        prev_selection = (
            set(addon_props.last_object_selection.split(",")) if addon_props.last_object_selection else set()
        )

        if current_selection == prev_selection and not force_run:
            if IS_DEBUG():
                print("[DEBUG] Object selection unchanged; skipping property list update.")
            return None

        if IS_DEBUG():
            print("------------- Continuous Property List Update -------------")

        # Queue the property list update
        def update_property_list():
            addon_props.custom_property_list.clear()

            # Add unique custom properties to the set
            unique_object_data_props = set()
            unique_mesh_data_props = set()
            for obj in bpy.context.selected_objects:
                # Object Properties
                for prop_name in obj.keys():
                    if IS_DEBUG():
                        print(f"[DEBUG] (OP) {obj.name} - {prop_name=}")
                    if not prop_name.startswith("_") and prop_name not in unique_object_data_props:
                        try:
                            unique_object_data_props.add(prop_name)
                            item = addon_props.custom_property_list.add()
                            item.name = prop_name
                            # Type is defaulted to Object
                        except Exception as e:
                            print(f"[ERROR] Error adding unique Custom Properties: {e}")
                            context_error_debug(error=e)

                # Object Data Properties
                if obj.data and obj.type == "MESH":
                    for prop_name in obj.data.keys():
                        if IS_DEBUG():
                            print(f"[DEBUG] (ODP) {obj.name} - {prop_name=}")
                        if not prop_name.startswith("_") and prop_name not in unique_mesh_data_props:
                            try:
                                unique_mesh_data_props.add(prop_name)
                                item = addon_props.custom_property_list.add()
                                item.name = prop_name
                                item.type = CUSTOM_PROPERTIES_TYPES.MESH_DATA
                            except Exception as e:
                                print(f"[ERROR] Error adding unique Object Data Custom Properties: {e}")
                                context_error_debug(error=e)

            # Update the last object selection
            try:
                addon_props.last_object_selection = ",".join(current_selection)
            except Exception as e:
                context_error_debug(
                    error=e,
                    extra_prints=[
                        f"addon_props.last_object_selection: {addon_props.last_object_selection}",
                        f"{current_selection=}",
                    ],
                )

            # Force UI update
            for area in bpy.context.screen.areas:
                if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                    area.tag_redraw()

        queue_op(update_property_list)
    else:
        # Clear the property list if no objects are selected
        def clear_property_list():
            try:
                addon_props.custom_property_list.clear()
                if IS_DEBUG():
                    print(f"Cleared UIList custom_property_list")
            except Exception as e:
                print(f"[ERROR] Error clearing custom property list when no selected objects: {e}")
                context_error_debug(error=e)
            try:
                addon_props.last_object_selection = ""
                if IS_DEBUG():
                    print(f"Cleared property last_object_selection")
            except Exception as e:
                print(f"[ERROR] Error setting last object selection when no selected objects: {e}")
                context_error_debug(error=e)

            # Force UI update
            for area in bpy.context.screen.areas:
                if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                    area.tag_redraw()

        queue_op(clear_property_list)

    return None


def update_data_scene_objects(scene, force_run=False):
    """
    Update tracking of objects in the scene and data

    This handler monitors changes to scene objects and
    updates internal references accordingly.
    """
    addon_props = get_addon_props()

    # Get current counts
    bpy_scene_objects_len = len(bpy.context.scene.objects)
    bpy_data_objects_len = len(bpy.data.objects)
    scene_objects_len = len(addon_props.scene_objects)
    data_objects_len = len(addon_props.data_objects)

    if IS_DEBUG():
        print("------------- Update Data Scene Objects -------------")
        print(f"[DEBUG] Scene {bpy_scene_objects_len} == {scene_objects_len}")
        print(f"[DEBUG] Data  {bpy_data_objects_len} == {data_objects_len}")

    # Check if counts have changed
    counts_changed = bpy_data_objects_len != data_objects_len or bpy_scene_objects_len != scene_objects_len

    if force_run or counts_changed:

        def update_object_references():
            if IS_DEBUG():
                print("------------- Updating Object References -------------")

            # Set the updated flag to True
            addon_props.objects_updated = True

            # Clear existing references
            addon_props.scene_objects.clear()
            addon_props.data_objects.clear()

            # Collect Scene Objects
            for obj in bpy.context.scene.objects:
                item = addon_props.scene_objects.add()
                item.object = obj

            # Collect Data Objects
            unused_objects = []
            for obj in bpy.data.objects:
                if obj.name in bpy.context.scene.objects:
                    item = addon_props.data_objects.add()
                    item.object = obj
                else:
                    unused_objects.append(obj)

            if IS_DEBUG() and unused_objects:
                print(f"Unused blocks to be cleared: {len(unused_objects)}")
                for unused in unused_objects:
                    print(f"[DEBUG] (DATA) {unused.name} not in Scene.")

        queue_op(update_object_references)
    else:
        # Reset the flag if no changes
        queue_op(lambda: setattr(addon_props, "objects_updated", False))


def cleanup_object_set_invalid_references(scene):
    """
    Remove invalid object references from object sets

    This cleans up references to deleted objects to prevent errors.
    """
    if IS_DEBUG():
        print("------------- Cleanup Object Sets Invalid References -------------")

    addon_props = get_addon_props()

    if IS_DEBUG():
        print(f"[DEBUG] {addon_props.objects_updated=}")

    if addon_props.objects_updated:
        for object_set in addon_props.object_sets:
            # Identify invalid objects without modifying anything
            invalid_objects = []
            for object_item in object_set.objects:
                obj = object_item.object
                if not is_valid_object_global(obj):
                    invalid_objects.append(obj)

            # Now safely remove the invalid objects
            if invalid_objects:

                def remove_invalid_objects(object_set, invalid_objects):
                    for obj in invalid_objects:
                        try:
                            object_set.remove_object(obj)
                        except Exception as e:
                            print(f"[ERROR] Failed to remove object from set: {e}")

                    print(f"Cleaned up {len(invalid_objects)} references for Object Set '{object_set.name}'")

                queue_op(remove_invalid_objects, object_set, invalid_objects)

        # Reset the flag after cleanup
        queue_op(lambda: setattr(addon_props, "objects_updated", False))

    # Force UI Update to reflect changes
    for area in bpy.context.screen.areas:
        if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
            area.tag_redraw()


# ==============================
# OPERATIONS
# ==============================


def op_clear_sharp_along_axis(axis: str):
    """
    Clear sharp edges along specified axis

    Args:
        axis: The axis to clear sharp edges along (X, Y, or Z)
    """
    print(f"\n=== Clear Sharp Along Axis {axis}")
    axis = str(axis).upper()

    threshold = get_addon_prefs().clear_sharp_axis_float_prop
    print(f"Threshold: {threshold}")

    # Collect select objects
    objects = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]

    print(f"Objects: {objects}")

    if not objects:
        return False

    for obj in objects:
        # Set the active object
        bpy.context.view_layer.objects.active = obj
        print(f"Iterating: {obj.name}")

        # Check the mode
        mode = obj.mode
        print(f"Mode: {mode}")

        # Access mesh data
        mesh = obj.data
        print(f"Mesh: {mesh}")

        # Store the selection mode
        # Tuple of Booleans for each of the 3 modes
        selection_mode = tuple(get_scene().tool_settings.mesh_select_mode)

        # Store initial selections
        # Vertices
        selected_vertices = [v.index for v in mesh.vertices if v.select]

        # Edges
        selected_edges = [e.index for e in mesh.edges if e.select]

        # Faces
        selected_faces = [f.index for f in mesh.polygons if f.select]

        # Deselect all vertices
        set_mode_edit()
        set_mesh_selection_vertex()
        deselect_all()
        set_mode_object()  # We're in Object mode so we can select stuff. Logic is weird.

        for idx, vertex in enumerate(mesh.vertices):
            if axis == "X":
                if math.isclose(vertex.co.x, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True

            if axis == "Y":
                if math.isclose(vertex.co.y, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True

            if axis == "Z":
                if math.isclose(vertex.co.z, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True

        # Enter Edit mode
        set_mode_edit()

        # Switch to edge mode
        set_mesh_selection_edge(use_extend=False, use_expand=False)

        # Clear the Sharp
        bpy.ops.mesh.mark_sharp(clear=True)

        # Restore the inital selections and mode
        if selection_mode[0] is True:
            set_mesh_selection_vertex()
            deselect_all()
            set_mode_object()
            for vert_idx in selected_vertices:
                mesh.vertices[vert_idx].select = True
        if selection_mode[1] is True:
            set_mesh_selection_edge()
            deselect_all()
            set_mode_object()
            for edge_idx in selected_edges:
                mesh.edges[edge_idx].select = True
        if selection_mode[2] is True:
            set_mesh_selection_face()
            deselect_all()
            set_mode_object()
            for face_idx in selected_faces:
                mesh.polygons[face_idx].select = True

        # Set back to Object mode
        set_object_mode(mode)


# ==============================
# BATCH PROCESSING
# ==============================


def safe_batch_operation(objects, operation_func, *args, **kwargs):
    """
    Safely perform an operation on multiple objects in batches

    Args:
        objects: List of objects to process
        operation_func: Function to call for each object
        *args: Additional arguments for operation_func
        **kwargs: Additional keyword arguments for operation_func
    """
    batch_size = 10  # Process objects in batches of 10

    for i in range(0, len(objects), batch_size):
        batch = objects[i : i + batch_size]

        def process_batch(batch_objects):
            for obj in batch_objects:
                try:
                    operation_func(obj, *args, **kwargs)
                except Exception as e:
                    print(f"[ERROR] Failed to process {obj.name}: {e}")

        queue_op(process_batch, batch)


# ==============================
# QUEUE SYSTEM & ERROR HANDLING
# ==============================


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


def context_error_debug(error: str = None, extra_prints: list = []):
    """Print debug information about the current context and error"""
    if not IS_DEBUG():
        return

    import inspect

    print(f"+" * 32)
    if error:
        print(f"[DEBUG] Associated Error (below):")
        print(f"[DEBUG] {error}")
        print()

    if bpy.app.background:
        print(f"[DEBUG] Running in background mode - ID writing may be restricted.")

    if bpy.ops.wm.save_as_mainfile.poll() == False:
        print(f"[DEBUG] Restricted context - file saving not allowed.")

    print(f"[DEBUG] bpy.context:", bpy.context)
    if bpy.context:
        print(f"[DEBUG] bpy.context.scene:", bpy.context.scene)
        print(f"[DEBUG] bpy.context.area:", bpy.context.area)
        print(f"[DEBUG] bpy.context.mode:", bpy.context.mode)
        print(f"[DEBUG] bpy.context.window:", bpy.context.window)
        print(f"[DEBUG] bpy.context.space_data:", bpy.context.space_data)
        print(f"[DEBUG] bpy.context.region:", bpy.context.region)
        print(f"[DEBUG] bpy.context.region_data:", bpy.context.region_data)
    print(f"[DEBUG] Window Manager debug mode:", bpy.app.debug_wm)

    print(f"[DEBUG] Current Handlers:")
    for handler in bpy.app.handlers.depsgraph_update_post:
        print(f"[DEBUG]    - {handler.__name__}")

    print(f"[DEBUG] Call Stack:")
    for frame in inspect.stack():
        print(f"[DEBUG]   File: {frame.filename}, Line: {frame.lineno}, Function: {frame.function}")

    if extra_prints:
        print()
        print(f"[DEBUG] Extra Prints")
        for extra_print in extra_prints:
            print(f"[DEBUG] Extra: {extra_print}")

    print(f"+" * 32)


# ==============================
# HANDLER WRAPPERS
# ==============================


def timer_update_data_scene_objects():
    """Timer compatible wrapper for update_data_scene_objects"""
    scene = bpy.context.scene
    queue_op(update_data_scene_objects, scene)
    return _QUEUE_RETRY_SECONDS


@bpy.app.handlers.persistent
def handler_update_data_scene_objects(scene):
    """Queue the update_data_scene_objects operation"""
    queue_op(update_data_scene_objects, scene)


@bpy.app.handlers.persistent
def timer_continuous_property_list_update():
    """Timer wrapper for continuous_property_list_update"""
    scene = bpy.context.scene
    ctx = bpy.context
    queue_op(continuous_property_list_update, scene, ctx)
    return _QUEUE_RETRY_SECONDS


@bpy.app.handlers.persistent
def handler_continuous_property_list_update(scene, context=None):
    """Queue the continuous_property_list_update operation"""
    ctx = context or bpy.context
    queue_op(continuous_property_list_update, scene, ctx)


def timer_cleanup_object_set_invalid_references():
    """Timer wrapper for cleanup_object_set_invalid_references"""
    scene = bpy.context.scene
    queue_op(cleanup_object_set_invalid_references, scene)
    # Run cleanup more frequently than other operations
    return _QUEUE_RETRY_SECONDS / 2 if _QUEUE_RETRY_SECONDS >= 1 else _QUEUE_RETRY_SECONDS


@bpy.app.handlers.persistent
def handler_cleanup_object_set_invalid_references(scene):
    """Queue the cleanup_object_set_invalid_references operation"""
    queue_op(cleanup_object_set_invalid_references, scene)


@bpy.app.handlers.persistent
def handler_on_load_refresh_object_sets_colours(dummy):
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
