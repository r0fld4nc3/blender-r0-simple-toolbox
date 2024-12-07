import bpy
import math

from .const import INTERNAL_NAME

class OBJECT_MODES:
    OBJECT = "OBJECT"
    EDIT = "EDIT"
    EDIT_MESH = "EDIT_MESH"
    SCULPT = "SCULPT"
    VERTEX_PAINT = "VERTEX_PAINT"
    TEXTURE_PAINT = "TEXTURE_PAINT"
    WEIGHT_PAINT = "WEIGHT_PAINT"


def get_scene() -> bpy.types.Scene:
    return bpy.context.scene

def get_scene_name() -> str:
    return get_scene().name

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

def select_object(obj: bpy.types.Object, add=True, set_active=False):
    print(f"Selecting {obj.name} {add=} {set_active=}")
    if not add:
        deselect_all()
    
    obj.select_set(True)

    if not add or set_active:
        set_active_object(obj)

def set_active_object(obj: bpy.types.Object):
    bpy.context.view_layer.objects.active = obj

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
        preferences = bpy.context.preferences.addons[INTERNAL_NAME].preferences
        value = preferences.zenuv_td_prop
        return value
    except Exception as e:
        print(e)
        return 10.0  # default value if preferences not found
    
def get_td_unit():
    """Get the texel density unit from addon preferences"""
    try:
        preferences = bpy.context.preferences.addons[INTERNAL_NAME].preferences
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
    axis = str(axis).upper()
    
    threshold = bpy.context.preferences.addons[INTERNAL_NAME].preferences.clear_sharp_axis_float_prop
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


def continuous_property_list_update(scene, context):
    # This method is required to assess the last object selection, otherwise
    # this is triggered on every click and the list is updated, and the checkboxes are reset
    
    if bpy.context.selected_objects:
        current_selection = {obj.name for obj in iter_scene_objects(selected=True)}
        addon_props = get_scene().r0fl_toolbox_props
        prev_selection = set(addon_props.last_object_selection.split(',')) if addon_props.last_object_selection else set()

        if current_selection != prev_selection:
            addon_props.custom_property_list.clear()

            # Add unique custom properties to the list
            unique_props = set()
            for obj in bpy.context.selected_objects:
                for prop_name in obj.keys():
                    if not prop_name.startswith('_') and prop_name not in unique_props:
                        unique_props.add(prop_name)
                        item = addon_props.custom_property_list.add()
                        item.name = prop_name

            # Update the last object selection
            addon_props.last_object_selection = ','.join(current_selection)
    else:
        # Clear the property list if no objects are selected
        get_scene().r0fl_toolbox_props.custom_property_list.clear()
        get_scene().r0fl_toolbox_props.last_object_selection = ""

def delete_custom_orientation(name: str):
    """
    What a stupid workaround....
    
    - https://blender.stackexchange.com/a/196080
    """

    print(f"Want to delete Transform Orientation: {name}")

    try:
        get_scene().transform_orientation_slots[0].type = ""
    except Exception as inst:
        transforms = str(inst).split("'")[1::2]

    transform_list = list(transforms)
    for enum_type in transform_list[7:]: # The 7 first orientations are built-ins
        get_scene().transform_orientation_slots[0].type = enum_type
        bpy.ops.transform.delete_orientation()