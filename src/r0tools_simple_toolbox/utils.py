import bpy
import math

from .const import INTERNAL_NAME, ADDON_NAME, DEBUG


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
    MESH = "MESH"
    CURVE = "CURVE"
    SURFACE = "SURFACE"
    META = "META"
    FONT = "FONT"
    CURVES = "CURVES"
    POINTCLOUD = "POINTCLOUD"
    VOLUME = "VOLUME"
    GPENCIL = "GPENCIL"
    GREASEPENCIL = "GREASEPENCIL"
    ARMATURE = "ARMATURE"
    LATTICE = "LATTICE"
    EMPTY = "EMPTY"
    LIGHT = "LIGHT"
    LIGHT_PROBE = "LIGHT_PROBE"
    CAMERA = "CAMERA"
    SPEAKER = "SPEAKER"


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

def draw_objects_sets_uilist(layout, context, object_sets_box=None):
    addon_prefs = get_addon_prefs()
    addon_props = get_addon_props()

    if DEBUG:
        print(f"[DEBUG] {layout=}")
        print(f"[DEBUG] {object_sets_box=}")

    # Object Sets Editor
    if object_sets_box:
        row = object_sets_box.row()
    elif layout:
        row = layout.row()
    else:
        print(f"[ERROR] No valid layout to use:\n{layout=}\n{object_sets_box=}")
        return False
    
    split = row.split(factor=0.9)

    # Left Section
    col = split.column()
    col.template_list(
        "R0PROP_UL_ObjectSetsList",
        "object_sets",
        addon_props,          # Collection owner
        "object_sets",        # Collection property
        addon_props,          # Active item owner
        "object_sets_index",  # Active item property
        rows=addon_prefs.object_sets_list_rows
    )

    # Right side
    col = split.column(align=True)
    col.operator("r0tools.add_object_set_popup")
    col.operator("r0tools.remove_object_set")
    if len(addon_props.object_sets) > 1: # Show buttons only when applicable
        col.label(text="") # Spacer
        col.operator("r0tools.move_object_set_item_up", icon='TRIA_UP', text="")
        col.operator("r0tools.move_object_set_item_down", icon='TRIA_DOWN', text="")

    # Bottom
    if object_sets_box:
        row = object_sets_box.row(align=True)
    else:
        row = layout.row(align=True)
    split = row.split(factor=0.65)
    row_col = split.row(align=True)
    row_col.operator("r0tools.add_to_object_set")
    row_col.operator("r0tools.remove_from_object_set")
    #
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
    - EDIT
    - SCULPT
    - VERTEX_PAINT
    - TEXTURE_PAINT
    - WEIGHT_PAINT
    """

    print(f"Setting mode: {mode}")
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

def select_object(obj: bpy.types.Object, add=True, set_active=False) -> bpy.types.Object | None:
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

def is_object_visible_in_viewport(obj):
    # Check if the object is set to be visible in the viewport
    if not obj.visible_get():
        if DEBUG:
            print(f"[DEBUG] {obj.name} is not visible in viewport.")
        return False
    
    if DEBUG:
        print(f"[DEBUG] {obj.name} is visible in viewport.")
        print(f"[DEBUG] Checking {obj.name} Collection(s).")

    # Check if the object's collection is visible in the viewport
    for collection in obj.users_collection:
        if DEBUG:
            print(f"[DEBUG]    - {collection.name}")
        if not collection.hide_viewport:
            if DEBUG:
                print(f"[DEBUG]    - {collection.name} is visible.")
            return True
        else:
            if DEBUG:
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
    bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text=message), title=title)
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

    return obj.visible_get(view_layer=ctx.view_layer)  # Returns True for visible objects

def object_visible(obj):
    # print(f"Object '{obj.name}' visible {obj.visible_get()}")
    return obj.visible_get() # Returns True for visible objects

def save_preferences():
    """Safely save user preferences without causing recursion"""
    try:
        if not hasattr(save_preferences, 'is_saving'):
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
        td_split = td_unit.split('_')
        
        if td_split and len(td_split) > 1:
            td_unit = td_split[1].lower()
        else:
            td_unit = 'cm' # Default
        
        return td_unit
    except Exception as e:
        print(e)
        return 'cm'  # default value if preferences not found

def op_clear_sharp_along_axis(axis: str):
    print(f"\n=== Clear Sharp Along Axis {axis}")
    axis = str(axis).upper()
    
    threshold = get_addon_prefs().clear_sharp_axis_float_prop
    print(f"Threshold: {threshold}")
    
    # Collect select objects
    objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
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
        set_mode_object() # We're in Object mode so we can select stuff. Logic is weird.
        
        for idx, vertex in enumerate(mesh.vertices):
            # print(f"Vertex {vertex.co}", end="")
            
            if axis == 'X':
                if math.isclose(vertex.co.x, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True
                    # print(f" X isclose({vertex.co.x}, 0.0, abs_tol={threshold}): {math.isclose(vertex.co.x, 0.0, abs_tol=threshold)}")
            
            if axis == 'Y':
                if math.isclose(vertex.co.y, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True
                    # print(f" Y isclose({vertex.co.y}, 0.0, abs_tol={threshold}): {math.isclose(vertex.co.y, 0.0, abs_tol=threshold)}")
                    
            if axis == 'Z':
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
def handler_continuous_property_list_update(scene, context, skip_sel_check=False):
    # This method is required to assess the last object selection, otherwise
    # this is triggered on every click and the list is updated, and the checkboxes are reset
    
    if bpy.context.selected_objects:
        current_selection = {obj.name for obj in iter_scene_objects(selected=True)}
        addon_props = get_addon_props()
        prev_selection = set(addon_props.last_object_selection.split(',')) if addon_props.last_object_selection else set()

        if DEBUG:
            print("------------- Continuous Property List Update -------------")
            print(f"[DEBUG] {skip_sel_check=}")
            
        if skip_sel_check or current_selection != prev_selection:
            try:
                addon_props.custom_property_list.clear()
            except Exception as e:
                print(f"[ERROR] Error clearing Custom Property list: {e}")
                # raise e

            # Add unique custom properties to the set
            unique_object_data_props = set()
            unique_mesh_data_props = set()
            for obj in bpy.context.selected_objects:
                # Object Properties
                for prop_name in obj.keys():
                    if DEBUG:
                        print(f"[DEBUG] (OP) {obj.name} - {prop_name=}")
                    if not prop_name.startswith('_') and prop_name not in unique_object_data_props:
                        try:
                            unique_object_data_props.add(prop_name)
                            item = addon_props.custom_property_list.add()
                            item.name = prop_name
                            # Type is defaulted to Object
                        except Exception as e:
                            print(f"[ERROR] Error adding unique Custom Properties: {e}")
                            # raise e
                        
                # Object Data Properties
                if obj.data and obj.type == 'MESH':
                    for prop_name in obj.data.keys():
                        if DEBUG:
                            print(f"[DEBUG] (ODP) {obj.name} - {prop_name=}")
                        if not prop_name.startswith('_') and prop_name not in unique_mesh_data_props:
                            try:
                                unique_mesh_data_props.add(prop_name)
                                item = addon_props.custom_property_list.add()
                                item.name = prop_name
                                item.type = CUSTOM_PROPERTIES_TYPES.MESH_DATA
                                # Type is defaulted to Object
                            except Exception as e:
                                print(f"[ERROR] Error adding unique Object Data Custom Properties: {e}")
                                # raise e

            # Update the last object selection
            addon_props.last_object_selection = ','.join(current_selection)
    else:
        # Clear the property list if no objects are selected
        try:
            get_addon_props().custom_property_list.clear()
        except Exception as e:
            print(f"[ERROR] Error clearing custom property list when no selected objects: {e}")
        try:
            get_addon_props().last_object_selection = ""
        except Exception as e:
            print(f"[ERROR] Error setting last object selection when no selected objects: {e}")

def get_builtin_transform_orientations(identifiers=False) -> list:
    if identifiers:
        _ret = [i.identifier for i in bpy.types.TransformOrientationSlot.bl_rna.properties['type'].enum_items]
    else:
        _ret = [i.name for i in bpy.types.TransformOrientationSlot.bl_rna.properties['type'].enum_items]
    
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

    transform_list = list(transforms)
    if DEBUG:
        print(f"[DEBUG] {transform_list=}")

    return transform_list

def delete_custom_transform_orientation(name: str):
    transform_list = get_custom_transform_orientations()
    for enum_type in transform_list:
        if DEBUG:
            print(f"[DEBUG] {enum_type=} == {name=}")
        if enum_type == name or str(enum_type).lower() == str(name).lower():
            get_scene().transform_orientation_slots[0].type = enum_type
            bpy.ops.transform.delete_orientation()

def get_custom_transform_orientations() -> list:
    """
    Returns a `list[str]` with just Custom Transform Orientation Enum Type names
    """

    custom_transforms= get_transform_orientations()[7:] # The 7 first orientations are built-ins
    if DEBUG:
        print(f"[DEBUG] {custom_transforms=}")

    return custom_transforms

def is_valid_object_global(obj):
    """Check if an object pointer is valid and exists in any scene. If not, assume dangling reference."""
    exists_mesh = obj and obj.name in bpy.data.objects and any(
        obj.name in scene.objects for scene in bpy.data.scenes
    )
    
    if not exists_mesh:
        print(f"Dangling reference: {obj.name}")
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
    if DEBUG:
        print("------------- Update Object Sets -------------")

    try:
        addon_props = get_addon_props()
        for object_set in addon_props.object_sets:
            object_set.update_count()
    except Exception as e:
        print(f"Error updating object sets: {e}")

@bpy.app.handlers.persistent
def handler_cleanup_object_set_invalid_references(scene):
    if DEBUG:
        print("------------- Cleanup Object Sets Invalid References -------------")

    addon_props = get_addon_props()

    if DEBUG:
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
                print(f"Cleaned up {cleaned_up} references for Object Set '{object_set.name}'")

@bpy.app.handlers.persistent
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

    if DEBUG:
        print("------------- Update Data Scene Objects -------------")
        print(f"[DEBUG] Data  {bpy_data_objects_len} == {len(data_objects)}")
        print(f"[DEBUG] Scene {bpy_scene_objects_len} == {len(scene_objects)}")

    if force_run or bpy_data_objects_len != len(data_objects) or bpy_scene_objects_len != len(scene_objects):
        if DEBUG:
            print("------------- Update Data Scene Objects -------------")

        unused_count = 0

        # Scene Objects
        try:
            addon_props.scene_objects.clear()
        except Exception as e:
            print(f"[ERROR] Error clearing scene_objects: {e}")

        for obj in bpy.context.scene.objects:
            try:
                item = addon_props.scene_objects.add()
                item.object = obj
            except Exception as e:
                print(f"[ERROR] Error adding new entry to scene_objects")
        
        # Data objects
        try:
            addon_props.data_objects.clear()
        except Exception as e:
            print(f"[ERROR] Error clearing data_objects: {e}")
            
        for obj in bpy.data.objects:
            if obj.name in bpy.context.scene.objects:
                item = addon_props.data_objects.add()
                item.object = obj
            else:
                unused_count += 1
                if DEBUG:
                    print(f"[DEBUG] (DATA) {obj.name} not in Scene.")

        if DEBUG:
            print(f"[DEBUG] {addon_props.data_objects}")
            print(f"[DEBUG] {addon_props.scene_objects}")

        if unused_count > 0:
            print(f"Unused blocks to be cleared: {unused_count}")
        
        addon_props.objects_updated = True
    else:
        addon_props.objects_updated = False
