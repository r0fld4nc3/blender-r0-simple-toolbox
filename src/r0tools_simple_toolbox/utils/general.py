import math

import bpy

from ..const import DEBUG
from ..utils import (
    CUSTOM_PROPERTIES_TYPES,
    OBJECT_MODES,
    get_addon_prefs,
    get_addon_props,
    get_scene,
)


def IS_DEBUG():
    """Return current debug state"""
    addon_prefs = get_addon_prefs()
    return DEBUG or addon_prefs.debug


# ==============================
# OBJECT, MESH, SELECTION
# ==============================


def set_active_object(obj: bpy.types.Object):
    """Set the active object in the current view layer"""
    bpy.context.view_layer.objects.active = obj


def get_active_object() -> bpy.types.Object | None:
    """Get the active object from the current view layer"""
    return bpy.context.view_layer.objects.active


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
    """
    try:
        exists_object = (
            obj is not None
            and obj
            and obj.name in bpy.data.objects
            and any(obj.name in scene.objects for scene in bpy.data.scenes)
        )

        if not exists_object:
            if IS_DEBUG():
                if obj is not None:
                    print(f"[DEBUG] [GENERAL] Dangling reference: {obj.name}")
                else:
                    print(f"[DEBUG] [GENERAL] Dangling reference: {obj}")
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


def _custom_properties_store_states() -> dict:
    addon_props = get_addon_props()

    # Store the current selection state of Custom Property List
    selection_state = {}
    for item in addon_props.custom_property_list:
        selection_state[(item.name, item.type)] = item.selected

    return selection_state


def custom_property_list_add_props(props: set | list, prop_type, selection_state: dict):
    addon_props = get_addon_props()

    # Populate the UIList
    for prop_name in props:
        try:
            item = addon_props.custom_property_list.add()
            item.name = prop_name
            item.type = prop_type
            # Restore selection state if it exists
            key = (prop_name, prop_type)
            if key in selection_state:
                item.selected = selection_state[key]
        except Exception as e:
            print(f"[ERROR] Error adding unique Custom Properties: {e}")
            context_error_debug(error=e)


def property_list_update(scene, context, force_run=False):
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

        if IS_DEBUG():
            print("------------- Custom Property List Update -------------")

        # Store the current selection state before clearing the list
        selection_state = _custom_properties_store_states()

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
                    unique_object_data_props.add(prop_name)

            # Object Data Properties
            if obj.data and obj.type == "MESH":
                for prop_name in obj.data.keys():
                    if IS_DEBUG():
                        print(f"[DEBUG] (ODP) {obj.name} - {prop_name=}")
                    if not prop_name.startswith("_") and prop_name not in unique_mesh_data_props:
                        unique_mesh_data_props.add(prop_name)

        # Populate the UIList
        # Allows it to finally be sorted!
        custom_property_list_add_props(unique_object_data_props, CUSTOM_PROPERTIES_TYPES.OBJECT_DATA, selection_state)
        custom_property_list_add_props(unique_mesh_data_props, CUSTOM_PROPERTIES_TYPES.MESH_DATA, selection_state)

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

    else:
        # Store the states even if nothing selected
        selection_state = _custom_properties_store_states()

        # Clear the property list if no objects are selected
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

    return None


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
