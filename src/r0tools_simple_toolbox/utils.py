import math

import bpy

from .const import DEBUG, INTERNAL_NAME


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


_TIMERS = {}


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
        col.label(text="")  # Spacer
        col.operator("r0tools.move_object_set_item_up", icon="TRIA_UP", text="")
        col.operator("r0tools.move_object_set_item_down", icon="TRIA_DOWN", text="")

    # Bottom
    if object_sets_box:
        parent = object_sets_box
    else:
        parent = layout
    row = parent.row(align=True)

    # Add/Remove Object Set Buttons
    split = row.split(factor=0.65)
    row_col = split.row(align=True)
    row_col.operator("r0tools.add_to_object_set")
    row_col.operator("r0tools.remove_from_object_set")
    # Select Object Set Button
    row_col = split.row()
    row_col.operator("r0tools.select_object_set")


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

    # print(f"Object '{obj.name}' visible view_layer {obj.visible_get(view_layer=ctx.view_layer)}")

    return obj.visible_get(
        view_layer=ctx.view_layer
    )  # Returns True for visible objects


def object_visible(obj):
    # print(f"Object '{obj.name}' visible {obj.visible_get()}")
    return obj.visible_get()  # Returns True for visible objects


def save_preferences():
    """Safely save user preferences without causing recursion"""
    try:
        if not hasattr(save_preferences, "is_saving"):
            save_preferences.is_saving = False

        if not save_preferences.is_saving:
            save_preferences.is_saving = True
            bpy.context.preferences.use_preferences_save = True

            get_scene().zen_uv.td_props.prp_current_td = get_td_value()
            get_scene().zen_uv.td_props.td_unit = get_td_unit()

            bpy.ops.wm.save_userpref()
            save_preferences.is_saving = False
    except Exception as e:
        print(f"Error saving preferences: {e}")
        save_preferences.is_saving = False


def schedule_timer_run(func, *args, interval=0.1, **kwargs):
    """Schedules the update function and ensures it runs only once per depsgraph update."""

    if func.__name__ in _TIMERS:
        return  # Prevent duplicate registrations

    def wrapper():
        try:
            func(*args, **kwargs)  # Run the function
        except Exception as e:
            print(f"Timer function {func.__name__} failed: {e}")
        finally:
            _TIMERS.pop(func.__name__, None)  # Remove from tracking after execution

        return None  # Ensure the timer runs only once

    _TIMERS[func.__name__] = wrapper
    bpy.app.timers.register(wrapper, first_interval=interval)


def get_td_value():
    """Get the texel density value from addon preferences"""
    try:
        preferences = get_addon_prefs()
        value = preferences.zenuv_td_prop
        return value
    except Exception as e:
        print(e)
        return 10.0  # default value if preferences not found


def get_td_unit():
    """Get the texel density unit from addon preferences"""
    try:
        preferences = get_addon_prefs()
        td_unit = preferences.zenuv_td_unit_prop
        td_split = td_unit.split("_")

        if td_split and len(td_split) > 1:
            td_unit = td_split[1].lower()
        else:
            td_unit = "cm"  # Default

        return td_unit
    except Exception as e:
        print(e)
        return "cm"  # default value if preferences not found


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
            # print(f"Vertex {vertex.co}", end="")

            if axis == "X":
                if math.isclose(vertex.co.x, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True
                    # print(f" X isclose({vertex.co.x}, 0.0, abs_tol={threshold}): {math.isclose(vertex.co.x, 0.0, abs_tol=threshold)}")

            if axis == "Y":
                if math.isclose(vertex.co.y, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True
                    # print(f" Y isclose({vertex.co.y}, 0.0, abs_tol={threshold}): {math.isclose(vertex.co.y, 0.0, abs_tol=threshold)}")

            if axis == "Z":
                if math.isclose(vertex.co.z, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True
                    # print(f" Z isclose({vertex.co.z}, 0.0, abs_tol={threshold}): {math.isclose(vertex.co.z, 0.0, abs_tol=threshold)}")

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


@bpy.app.handlers.persistent
def handler_continuous_property_list_update(scene, context):
    schedule_timer_run(continuous_property_list_update, scene, context)


def continuous_property_list_update(scene, context, force_run=False):
    # This method is required to assess the last object selection, otherwise
    # this is triggered on every click and the list is updated, and the checkboxes are reset

    addon_props = get_addon_props()

    if not addon_props.show_custom_property_list_prop and not force_run:
        # Rerun if panel is now visible, alleviates some computation
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
                        # raise e

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
                            # raise e

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
    else:
        # Clear the property list if no objects are selected
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

    for area in bpy.context.screen.areas:
        if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
            area.tag_redraw()  # Force UI Update to reflect changes :)

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


@bpy.app.handlers.persistent
def handler_update_object_set_count(context):
    if IS_DEBUG():
        print("------------- Update Object Sets -------------")

    try:
        addon_props = get_addon_props()
        for object_set in addon_props.object_sets:
            object_set.update_count()
    except Exception as e:
        print(f"[ERROR] Error updating object sets: {e}")
        context_error_debug(error=e)

    for area in bpy.context.screen.areas:
        if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
            area.tag_redraw()  # Force UI Update to reflect changes :)


@bpy.app.handlers.persistent
def handler_cleanup_object_set_invalid_references(scene):
    schedule_timer_run(cleanup_object_set_invalid_references, scene)


def cleanup_object_set_invalid_references(scene):
    if IS_DEBUG():
        print("------------- Cleanup Object Sets Invalid References -------------")

    addon_props = get_addon_props()

    if IS_DEBUG():
        print(f"[DEBUG] {addon_props.objects_updated=}")

    if addon_props.objects_updated:
        for object_set in addon_props.object_sets:
            old_len = len(object_set.objects)

            # Collect objects
            for object_item in reversed(object_set.objects):
                obj = object_item.object
                if not is_valid_object_global(obj):
                    object_set.remove_object(obj)

            cleaned_up = old_len - len(object_set.objects)

            if cleaned_up > 0:
                print(
                    f"Cleaned up {cleaned_up} references for Object Set '{object_set.name}'"
                )

    for area in bpy.context.screen.areas:
        if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
            area.tag_redraw()  # Force UI Update to reflect changes :)


@bpy.app.handlers.persistent
def handler_update_data_scene_objects(scene, force_run=False):
    schedule_timer_run(update_data_scene_objects, scene, force_run=force_run)


def update_data_scene_objects(scene, force_run=False):
    """
    Handler method to keep track of objects in `bpy.data.objects` and `bpy.context.scene.objects`
    in order to determine if there were changes in object count.

    Used to trigger or accept certain methods that better rely on object count changes.

    To determine if there was an object change, it can be tested with:

    `if bpy.context.scene.r0fl_toolbox_props.objects_updated == bool:`

    `if bpy.context.scene.r0fl_toolbox_props.objects_updated:`
    """
    addon_props = get_addon_props()

    data_objects = addon_props.data_objects
    scene_objects = addon_props.scene_objects

    bpy_scene_objects_len = len(bpy.context.scene.objects)
    bpy_data_objects_len = len(bpy.data.objects)

    # Reset updated to False
    addon_props.objects_updated = False

    if IS_DEBUG():
        print("------------- Update Data Scene Objects -------------")
        print(f"[DEBUG] Scene {bpy_scene_objects_len} == {len(scene_objects)}")
        print(f"[DEBUG] Data  {bpy_data_objects_len} == {len(data_objects)}")

    if (
        force_run
        or bpy_data_objects_len != len(data_objects)
        or bpy_scene_objects_len != len(scene_objects)
    ):
        if IS_DEBUG():
            print("------------- Update Data Scene Objects -------------")

        unused_count = 0

        # Clear Scene Objects Reference
        try:
            addon_props.scene_objects.clear()
            if IS_DEBUG():
                print(f"Clear addon_props.scene_objects")
        except Exception as e:
            print(f"[ERROR] Error clearing scene_objects: {e}")
            if IS_DEBUG():
                context_error_debug(error=e)

        # Collect Scene Objects
        for obj in bpy.context.scene.objects:
            try:
                item = addon_props.scene_objects.add()
                item.object = obj
            except Exception as e:
                print(f"[ERROR] Error adding new entry to scene_objects: {e}")
                if IS_DEBUG():
                    context_error_debug(error=e)

        # Clear Data Objects
        try:
            addon_props.data_objects.clear()
        except Exception as e:
            print(f"[ERROR] Error clearing data_objects: {e}")
            if IS_DEBUG():
                context_error_debug(error=e)

        # Collect Data Objects
        errors = []
        unused_objects = []
        for obj in bpy.data.objects:
            try:
                if obj.name in bpy.context.scene.objects:
                    item = addon_props.data_objects.add()
                    item.object = obj
                else:
                    unused_count += 1
                    unused_objects.append(obj)
            except Exception as e:
                print(f"[ERROR] Error adding new entry to data_objects: {e}")
                if IS_DEBUG():
                    context_error_debug(error=e, extra_prints=[f"Obj Name: {obj.name}"])
                errors.append(e)

        if IS_DEBUG():
            print(f"[DEBUG] {addon_props.data_objects}")
            print(f"[DEBUG] {addon_props.scene_objects}")
            if errors:
                context_error_debug(error="\n".join(errors))

        if unused_count > 0:
            addon_props.objects_updated = True
            if IS_DEBUG():
                print(f"Unused blocks to be cleared: {unused_count}")
            for unused in unused_objects:
                if IS_DEBUG():
                    print(f"[DEBUG] (DATA) {unused.name} not in Scene.")

        if IS_DEBUG():
            print(f"[DEBUG] Objects Updated = {addon_props.objects_updated}")
    else:
        try:
            addon_props.objects_updated = False
        except Exception as e:
            print(f"[ERROR] Error setting objects_updated = False: {e}")
            if IS_DEBUG():
                context_error_debug(error=e)


def context_error_debug(error: str = None, extra_prints: list = []):
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


def set_show_all_operators(show: bool):
    """While Blender logs operators in the Info editor, this only reports operators with the `REGISTER` option enabled so as not to flood the Info view with calls to `bpy.ops.view3d.smoothview` and `bpy.ops.view3d.zoom`.

    Yet for testing it can be useful to see every operator called in a terminal, do this by enabling the debug option either by passing the `--debug-wm` argument when starting Blender or by setting `bpy.app.debug_wm` to True while Blender is running.
    """

    bpy.app.debug_wm = show

    print(f"Set Show All Operators to {show}")


def IS_DEBUG() -> bool:
    addon_prefs = get_addon_prefs()
    return DEBUG or addon_prefs.debug


def unregister():
    global _TIMERS
    for func_name, wrapper in _TIMERS.items():
        try:
            print(f"[_TIMERS] Unregistering timer function: {func_name}")
            bpy.app.timers.unregister(wrapper)
        except Exception as e:
            print(
                f"[_TIMERS] Unregistering timer function fail: At one point registered {func_name} but it is not longer registered in timers."
            )

    _TIMERS.clear()
