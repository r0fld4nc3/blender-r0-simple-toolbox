import math
import queue
from pathlib import Path

import bpy

from .const import DEBUG, INTERNAL_NAME

# Global state tracking
_ADDON_IN_ERROR_STATE = False

_QUEUE_RETRY_SECONDS = 1.0

_operation_queue = queue.Queue()

# fmt: off
class CUSTOM_PROPERTIES_TYPES:
    OBJECT_DATA = "OBJECT DATA"
    MESH_DATA   = "MESH DATA"


class OBJECT_MODES:
    OBJECT        = "OBJECT"
    EDIT          = "EDIT"
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


def draw_objects_sets_uilist(layout, context, object_sets_box=None):
    addon_prefs = get_addon_prefs()
    addon_props = get_addon_props()

    # Object Sets Editor
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

    # if addon_prefs.object_sets_use_colour:
    #    row = parent.row()
    #    row.prop(addon_prefs, "object_sets_default_colour", text="Default Colour")

    # Object Sets Row Number Slider (Same as in addon preferences)
    row = parent.row()
    row.prop(addon_prefs, "object_sets_list_rows", text="Rows:")

    row = parent.row()
    split = row.split(factor=0.92)  # Affects right side button width

    # Left Section
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

    # Right side
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


def get_scene() -> bpy.types.Scene:
    return bpy.context.scene


def get_scene_name() -> str:
    return get_scene().name


def get_context_area() -> str | None:
    if not bpy.context.area:
        return None

    return bpy.context.area.ui_type


def get_addon_props():
    return get_scene().r0fl_toolbox_props


def get_addon_prefs():
    return bpy.context.preferences.addons[INTERNAL_NAME].preferences


def get_addon_fs_path() -> Path:
    return Path(__file__).resolve().parent.parent


def set_object_mode(mode: str):
    """
    Set the current mode to one of the following:

    - OBJECT
    - EDIT (EDIT_MESH)
    - SCULPT
    - VERTEX_PAINT
    - TEXTURE_PAINT
    - WEIGHT_PAINT
    """

    if IS_DEBUG():
        print(f"Setting mode: {mode}")

    # Edit Mode weirdness fix
    if mode.upper() == "EDIT_MESH":
        mode = OBJECT_MODES.EDIT
    bpy.ops.object.mode_set(mode=mode)


def set_mode_object():
    """
    Sets the current mode to: Object Mode
    """
    set_object_mode("OBJECT")


def set_mode_edit():
    """
    Sets the current mode to: Edit Mode
    """
    set_object_mode("EDIT")


def select_object(
    obj: bpy.types.Object, add=True, set_active=False
) -> bpy.types.Object | None:
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
    if IS_DEBUG():
        print(f"Deselecting {obj.name}")

    if not is_valid_object_global(obj):
        return None

    try:
        obj.select_set(False)
    except Exception as e:
        print(f"[ERROR] Selecting {obj.name} {e}")

    return obj


def set_active_object(obj: bpy.types.Object):
    bpy.context.view_layer.objects.active = obj


def get_active_object() -> bpy.types.Object | None:
    return bpy.context.view_layer.objects.active


def is_object_visible_in_viewport(obj):
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


# Set selection mode template
def _set_mesh_selection_mode(use_extend=False, use_expand=False, type=""):
    bpy.ops.mesh.select_mode(use_extend=use_extend, use_expand=use_expand, type=type)


# Set selection mode Vertex
def set_mesh_selection_vertex(*args, **kwargs):
    kwargs["type"] = "VERT"
    _set_mesh_selection_mode(*args, **kwargs)


# Set selection mode Edge
def set_mesh_selection_edge(*args, **kwargs):
    kwargs["type"] = "EDGE"
    _set_mesh_selection_mode(*args, **kwargs)


# Set selection mode Face
def set_mesh_selection_face(*args, **kwargs):
    kwargs["type"] = "FACE"
    _set_mesh_selection_mode(*args, **kwargs)


def iter_scene_objects(selected=False, types: list[str] = []):
    iters = bpy.data.objects
    if selected:
        iters = bpy.context.selected_objects

    for o in iters:
        if not types or o.type in types:
            yield o


def iter_children(p_obj, recursive=True):
    """
    Iterate through all children of a given parent object.
    Args:
        p_obj: Parent object to find children for
        recursive: If True, also iterate through children of children
    """

    for obj in bpy.data.objects:
        if obj.parent == p_obj:
            yield obj
            if recursive:
                yield from iter_children(obj, recursive=True)


def show_notification(message, title="Script Finished"):
    """Display a popup notification and status info message"""
    bpy.context.window_manager.popup_menu(
        lambda self, context: self.layout.label(text=message), title=title
    )
    bpy.context.workspace.status_text_set(message)


def deselect_all():
    context_mode = bpy.context.mode
    edit_modes = ["EDIT", "EDIT_MODE"]
    object_modes = ["OBJECT", "OBJECT_MODE"]

    if context_mode in edit_modes:
        bpy.ops.mesh.select_all(action="DESELECT")
    elif context_mode in object_modes:
        bpy.ops.object.select_all(action="DESELECT")


def object_in_view_layer(obj, context=None):
    ctx = bpy.context
    if context:
        ctx = context

    return obj.visible_get(view_layer=ctx.view_layer)


def object_visible(obj):
    return obj.visible_get()


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


def process_queue_ops():
    """Process operations from the queue in the main thread"""
    try:
        # Process up to 100 operations
        operations_processed = 0
        max_operations_per_frame = 100

        while (
            not _operation_queue.empty()
            and operations_processed < max_operations_per_frame
        ):
            operation = _operation_queue.get_nowait()
            if IS_DEBUG():
                print(f"[DEBUG] Got Op: {operation}")
            try:
                operation()
                operations_processed += 1
            except Exception as e:
                print(f"[ERROR] Failed to execute queued operation: {e}")
                global _ADDON_IN_ERROR_STATE
                _ADDON_IN_ERROR_STATE = True
                if IS_DEBUG():
                    print(f"[DEBUG] Processed: {operations_processed}")
                    print(f"[DEBUG] {_operation_queue}")
            finally:
                _operation_queue.task_done()
                if IS_DEBUG():
                    print(f"[DEBUG] Done: {operation}")

        if not _operation_queue.empty():
            if IS_DEBUG():
                print()
            return 0.01  # Re-run in X second(s)

        # If we're in an error state, schedule recovery
        if _ADDON_IN_ERROR_STATE:
            if IS_DEBUG():
                print()
            return _QUEUE_RETRY_SECONDS

        # Check again in X second(s)
        if IS_DEBUG():
            print()
        return _QUEUE_RETRY_SECONDS

    except Exception as e:
        print(f"[ERROR] Error in process_queue_ops: {e}")
        return 1.0  # Retry in X second(s)


def queue_op(operation, *args, **kwargs):
    """Queue an operation to be executed in the main thread"""
    if args or kwargs:
        _operation_queue.put(lambda: operation(*args, **kwargs))
    else:
        _operation_queue.put(operation)


def get_uvmap_size_x():
    """Get selected UV Map Size in X"""
    addon_props = get_addon_props()
    uv_size_x = int(addon_props.uv_size_x)

    return uv_size_x


def get_uvmap_size_y():
    """Get selected UV Map Size in Y"""
    addon_props = get_addon_props()
    uv_size_y = int(addon_props.uv_size_y)

    return uv_size_y


def op_clear_sharp_along_axis(axis: str):
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
        bpy.context.view_layer.objects.active = obj
        print(f"Iterating: {obj.name}")

        mode = obj.mode
        print(f"Mode: {mode}")

        mesh = obj.data
        print(f"Mesh: {mesh}")

        # Store the selection mode
        # Tuple of Booleans for each of the 3 modes
        selection_mode = tuple(get_scene().tool_settings.mesh_select_mode)

        # Store initial selections
        selected_vertices = [v.index for v in mesh.vertices if v.select]
        selected_edges = [e.index for e in mesh.edges if e.select]
        selected_faces = [f.index for f in mesh.polygons if f.select]

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

        set_mode_edit()

        # Set to edge mode
        set_mesh_selection_edge(use_extend=False, use_expand=False)

        # Clear sharps
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


def continuous_property_list_update(scene, context, force_run=False):
    """Update property list based on selected objects"""
    addon_props = get_addon_props()

    if not addon_props.show_custom_property_list_prop and not force_run:
        # Re-run if panel is now visible, alleviates some computation
        if IS_DEBUG():
            print(
                f"[DEBUG] Custom Properties Panel is not visible, exiting from running continuous property list update."
            )
        return None

    if bpy.context.selected_objects or force_run:
        current_selection = {obj.name for obj in iter_scene_objects(selected=True)}
        prev_selection = (
            set(addon_props.last_object_selection.split(","))
            if addon_props.last_object_selection
            else set()
        )

        if current_selection == prev_selection and not force_run:
            if IS_DEBUG():
                print(
                    "[DEBUG] Object selection unchanged; skipping property list update."
                )
            return None

        if IS_DEBUG():
            print("------------- Continuous Property List Update -------------")

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
                    if (
                        not prop_name.startswith("_")
                        and prop_name not in unique_object_data_props
                    ):
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
                        if (
                            not prop_name.startswith("_")
                            and prop_name not in unique_mesh_data_props
                        ):
                            try:
                                unique_mesh_data_props.add(prop_name)
                                item = addon_props.custom_property_list.add()
                                item.name = prop_name
                                item.type = CUSTOM_PROPERTIES_TYPES.MESH_DATA
                                # Type is defaulted to Object
                            except Exception as e:
                                print(
                                    f"[ERROR] Error adding unique Object Data Custom Properties: {e}"
                                )
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
                print(
                    f"[ERROR] Error clearing custom property list when no selected objects: {e}"
                )
                context_error_debug(error=e)
            try:
                addon_props.last_object_selection = ""
                if IS_DEBUG():
                    print(f"Cleared property last_object_selection")
            except Exception as e:
                print(
                    f"[ERROR] Error setting last object selection when no selected objects: {e}"
                )
                context_error_debug(error=e)

            # Force UI update
            for area in bpy.context.screen.areas:
                if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                    area.tag_redraw()

        queue_op(clear_property_list)

    return None


def get_builtin_transform_orientations(identifiers=False) -> list:
    if identifiers:
        _ret = [
            i.identifier
            for i in bpy.types.TransformOrientationSlot.bl_rna.properties[
                "type"
            ].enum_items
        ]
    else:
        _ret = [
            i.name
            for i in bpy.types.TransformOrientationSlot.bl_rna.properties[
                "type"
            ].enum_items
        ]

    return _ret


def get_transform_orientations() -> list:
    """
    Returns a `list[str]` with all Transform Orientation Enum Type names
    """

    """
    What a stupid workaround....

    - https://blender.stackexchange.com/a/196080
    """
    try:
        # This is a problem because when trying to call this for a Pie Menu, it will error with:
        # AttributeError('Writing to ID classes in this context is not allowed: Scene, Scene datablock, error setting TransformOrientationSlot.type')
        # And won't produce any custom orientations
        get_scene().transform_orientation_slots[0].type = ""
    except Exception as inst:
        transforms = str(inst).split("'")[1::2]
        # context_error_debug(error=inst) # Fake error as we want it to spit out the built-ins

    transform_list = list(transforms)
    if IS_DEBUG():
        print(f"[DEBUG] {transform_list=}")

    return transform_list


def delete_custom_transform_orientation(name: str):
    transform_list = get_custom_transform_orientations()
    for enum_type in transform_list:
        if IS_DEBUG():
            print(f"[DEBUG] {enum_type=} == {name=}")
        if enum_type == name or str(enum_type).lower() == str(name).lower():
            get_scene().transform_orientation_slots[0].type = enum_type
            bpy.ops.transform.delete_orientation()


def get_custom_transform_orientations() -> list:
    """
    Returns a `list[str]` with just Custom Transform Orientation Enum Type names
    """

    custom_transforms = get_transform_orientations()[
        7:
    ]  # The 7 first orientations are built-ins
    if IS_DEBUG():
        print(f"[DEBUG] {custom_transforms=}")

    return custom_transforms


def is_valid_object_global(obj):
    """Check if an object pointer is valid and exists in any scene. If not, assume dangling reference."""
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


def get_depsgraph():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return depsgraph


def get_depsgraph_is_updated_geometry() -> bool:
    d = get_depsgraph()

    for update in d.updates:
        return update.is_updated_geometry

    return False


def get_depsgraph_is_updated_shading() -> bool:
    d = get_depsgraph()

    for update in d.updates:
        return update.is_updated_shading

    return False


def get_depsgraph_is_updated_transform() -> bool:
    d = get_depsgraph()

    for update in d.updates:
        return update.is_updated_transform

    return False


def cleanup_object_set_invalid_references(scene):
    """Remove invalid object references from object sets"""
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

                    print(
                        f"Cleaned up {len(invalid_objects)} references for Object Set '{object_set.name}'"
                    )

                queue_op(remove_invalid_objects, object_set, invalid_objects)

        # Reset the flag after cleanup
        queue_op(lambda: setattr(addon_props, "objects_updated", False))

    # Force UI Update to reflect changes
    for area in bpy.context.screen.areas:
        if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
            area.tag_redraw()


def update_data_scene_objects(scene, force_run=False):
    """
    Handler method to keep track of objects in `bpy.data.objects` and `bpy.context.scene.objects`
    to determine if there were changes in object count.
    """
    addon_props = get_addon_props()

    bpy_scene_objects_count = len(bpy.context.scene.objects)
    bpy_data_objects_count = len(bpy.data.objects)
    addon_scene_objects_count = len(addon_props.scene_objects)
    addon_data_objects_count = len(addon_props.data_objects)

    if IS_DEBUG():
        print("------------- Update Data Scene Objects -------------")
        print(f"[DEBUG] Scene {bpy_scene_objects_count} == {addon_scene_objects_count}")
        print(f"[DEBUG] Data  {bpy_data_objects_count} == {addon_data_objects_count}")

    counts_changed = (
        bpy_data_objects_count != addon_data_objects_count
        or bpy_scene_objects_count != addon_scene_objects_count
    )

    if force_run or counts_changed:

        def update_object_references():
            if IS_DEBUG():
                print("------------- Updating Object References -------------")

            addon_props.objects_updated = True

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

            if IS_DEBUG():
                if unused_objects:
                    print(f"Unused blocks to be cleared: {len(unused_objects)}")
                    for unused in unused_objects:
                        print(f"[DEBUG] (DATA) {unused.name} not in Scene.")

        queue_op(update_object_references)
    else:
        # Reset the flag if no changes
        queue_op(lambda: setattr(addon_props, "objects_updated", False))


def run_in_main_thread(function, *args, **kwargs):
    """
    Safely schedule a function to run in the main thread.
    This function can be called from any thread.

    Args:
        function: The function to execute in the main thread
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    """
    queue_op(function, *args, **kwargs)


def force_redraw_all():
    """Force a redraw of all UI areas"""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def recover_from_error_state():
    """Attempt to recover from an error state"""
    global _ADDON_IN_ERROR_STATE

    if not _ADDON_IN_ERROR_STATE:
        return

    print("[UTILS] [RECOVERY] Attempting to recover from error state...")

    # Clear the operation queue
    while not _operation_queue.empty():
        try:
            _operation_queue.get_nowait()
            _operation_queue.task_done()
        except:
            pass

    _ADDON_IN_ERROR_STATE = False

    # Force a clean state for the addon
    print("[UTILS] [RECOVERY] Error state cleared")

    # Force UI update to reflect recovery
    for area in bpy.context.screen.areas:
        area.tag_redraw()

    return True


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
        print(
            f"[DEBUG]   File: {frame.filename}, Line: {frame.lineno}, Function: {frame.function}"
        )

    if extra_prints:
        print()
        print(f"[DEBUG] Extra Prints")
        for extra_print in extra_prints:
            print(f"[DEBUG] Extra: {extra_print}")

    print(f"+" * 32)


def IS_DEBUG() -> bool:
    """Check if debug mode is enabled"""
    addon_prefs = get_addon_prefs()
    return DEBUG or addon_prefs.debug


def timer_update_data_scene_objects():
    """Timer compatible wrapper for update_data_scene_objects"""
    try:
        scene = bpy.context.scene
        queue_op(update_data_scene_objects, scene)
    except Exception as e:
        print(f"[ERROR] in timer_update_data_scene_objects: {e}")
    return _QUEUE_RETRY_SECONDS


@bpy.app.handlers.persistent
def handler_update_data_scene_objects(scene):
    """Queue the update_data_scene_objects operation"""
    queue_op(update_data_scene_objects, scene)


def timer_continuous_property_list_update():
    """Timer compatible wrapper for continuous_property_list_update"""
    try:
        scene = bpy.context.scene
        ctx = bpy.context
        queue_op(continuous_property_list_update, scene, ctx)
    except Exception as e:
        print(f"[ERROR] in timer_continuous_property_list_update: {e}")
    return _QUEUE_RETRY_SECONDS


@bpy.app.handlers.persistent
def handler_continuous_property_list_update(scene, context=None):
    """Queue the continuous_property_list_update operation"""
    ctx = context or bpy.context
    queue_op(continuous_property_list_update, scene, ctx)


def timer_cleanup_object_set_invalid_references():
    """Timer compatible wrapper for cleanup_object_set_invalid_references"""
    try:
        scene = bpy.context.scene
        queue_op(cleanup_object_set_invalid_references, scene)
    except Exception as e:
        print(f"[ERROR] in timer_cleanup_object_set_invalid_references: {e}")
    return (
        _QUEUE_RETRY_SECONDS / 2 if _QUEUE_RETRY_SECONDS >= 1 else _QUEUE_RETRY_SECONDS
    )


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
