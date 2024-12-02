import bpy
import gpu
import math
import bmesh
import json
from mathutils import Vector
from bpy_extras import view3d_utils

bl_info = {
    "name": "r0Tools - Quick Toolbox",
    "author": "Artur Rosário",
    "version": (0, 0, 5),
    "blender": (4, 2, 1),
    "location": "3D View",
    "description": "Utility to help clear different kinds of Data",
    "warning": "",
    "doc_url": "",
    "category": "Object"
}

vertex_shader = '''
uniform mat4 ModelViewProjectionMatrix;
in vec3 pos;

void main() {
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);
}
'''

fragment_shader = '''
out vec4 fragColor;

void main() {
    fragColor = vec4(1.0, 0.0, 0.0, 0.1); // Red with 90% transparency
}
'''

shader = gpu.types.GPUShader(vertex_shader, fragment_shader)

# Store the faces to highlight for each object
highlight_faces = {}

def create_batch(coords):
    """Create a GPU batch for drawing triangles."""
    # Create a vertex buffer
    format = gpu.types.GPUVertFormat()
    pos_id = format.attr_add(id="pos", comp_type='F32', len=3, fetch_mode='FLOAT')

    vert_buf = gpu.types.GPUVertBuf(format=format, len=len(coords))
    vert_buf.attr_fill(id=pos_id, data=coords)

    # Create a batch from the vertex buffer
    return gpu.types.GPUBatch(type='TRIS', buf=vert_buf)

def draw_highlight_callback():
    """Callback to draw highlighted polygons in the viewport."""
    if not highlight_faces:
        return

    shader.bind()

    for obj_name, faces in highlight_faces.items():
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != 'MESH':
            continue

        mesh = obj.data
        model_matrix = obj.matrix_world
        shader.uniform_float("ModelViewProjectionMatrix", bpy.context.region_data.perspective_matrix @ model_matrix)

        for face_idx in faces:
            face = mesh.polygons[face_idx]
            coords = [obj.matrix_world @ mesh.vertices[v].co for v in face.vertices]

            # Create and draw a batch for the face
            batch = create_batch(coords)
            batch.draw(shader)

def update_highlights(precomputed_faces):
    """
    Update the list of faces to highlight based on a precomputed dictionary.

    Args:
        precomputed_faces (dict): A dictionary where the keys are object names and
                                   the values are lists of polygon indices to highlight.
    """
    global highlight_faces
    highlight_faces = precomputed_faces  # Directly use the precomputed data

class OP_HighlightFacesGPU(bpy.types.Operator):
    bl_label = "Highlight Faces with GPU"
    bl_idname = "r0tools.gpu_highlight_faces"
    bl_description = "Highlight faces using GPU shaders based on precomputed data"
    bl_options = {'REGISTER'}

    precomputed_faces: bpy.props.StringProperty(
        name="Precomputed Faces",
        description="JSON string of precomputed faces to highlight"
    )

    _draw_handler = None

    def invoke(self, context, event):
        # Parse the precomputed data
        try:
            precomputed_faces = json.loads(self.precomputed_faces)
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"Invalid precomputed data: {e}")
            return {'CANCELLED'}

        # Update the highlights
        update_highlights(precomputed_faces)

        # Register the draw handler if not already done
        if OP_HighlightFacesGPU._draw_handler is None:
            OP_HighlightFacesGPU._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_highlight_callback, (), 'WINDOW', 'POST_VIEW'
            )

        context.area.tag_redraw()
        return {'FINISHED'}


# Operator to remove the draw callback
class OP_ClearGPUHighlights(bpy.types.Operator):
    bl_label = "Clear GPU Highlights"
    bl_idname = "r0tools.gpu_clear_highlights"
    bl_description = "Clear GPU-based face highlights"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if OP_HighlightFacesGPU._draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(
                OP_HighlightFacesGPU._draw_handler, 'WINDOW'
            )
            OP_HighlightFacesGPU._draw_handler = None

        global highlight_faces
        highlight_faces = {}  # Clear highlights
        context.area.tag_redraw()
        self.report({'INFO'}, "GPU highlights cleared")
        return {'FINISHED'}

# ============ ADDON PREFS =============
class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    experimental_features: bpy.props.BoolProperty(
        name="Experimental Features",
        description="Enable experimental features",
        default=False
    )
    
    clear_sharp_axis_float_prop: bpy.props.FloatProperty(
        name="clear_sharp_axis_float_prop",
        default=0.0,
        min=0.0,
        description="Threshold value for vertex/edge selection",
        update=lambda self, context: save_preferences()
    )
    
    zenuv_td_prop: bpy.props.FloatProperty(
        name="zenuv_td_prop",
        default=10.0,
        min=0.0,
        description="Texel Density value to apply to meshes",
        update=lambda self, context: save_preferences()
    )
    
    zenuv_unit_options = zenuv_unit_options = [
        ('PX_KM', "px/km", "Pixels per kilometer", 0),
        ('PX_M', "px/m", "Pixels per meter", 1),
        ('PX_CM', "px/cm", "Pixels per centimeter", 2),
        ('PX_MM', "px/mm", "Pixels per millimeter", 3),
        ('PX_UM', "px/um", "Pixels per micrometer", 4),
        ('PX_MIL', "px/mil", "Pixels per mil", 5),
        ('PX_FT', "px/ft", "Pixels per foot", 6),
        ('PX_IN', "px/in", "Pixels per inch", 7),
        ('PX_TH', "px/th", "Pixels per thou", 8)
    ]
    zenuv_td_unit_prop: bpy.props.EnumProperty(
        name="zenuv_td_unit_prop",
        items=zenuv_unit_options,
        description="Texel Density value to apply to meshes",
        default='PX_CM',
        update=lambda self, context: save_preferences()
    )
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        row = layout.row()
        row.prop(self, "experimental_features", text="Experimental Features")

        layout.prop(self, "clear_sharp_axis_float_prop", text="Clear Sharp Edges Threshold")
        
        # Box for texel density settings
        td_box = layout.box()
        td_box.label(text="Texel Density Settings")
        
        # Add the dropdown and value field in separate rows
        row = td_box.row()
        row.prop(self, "zenuv_td_prop")
        
        row = td_box.row()
        row.prop(self, "zenuv_td_unit_prop")
        
    def save_axis_threshold(self):
        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        addon_prefs.clear_sharp_axis_float_prop = self.clear_sharp_axis_float_prop
        # print(f"Saved Property: clear_sharp_axis_float_prop -> {self.clear_sharp_axis_float_prop}")


def save_preferences():
    """Safely save user preferences without causing recursion"""
    try:
        if not hasattr(save_preferences, 'is_saving'):
            save_preferences.is_saving = False
            
        if not save_preferences.is_saving:
            save_preferences.is_saving = True
            bpy.context.preferences.use_preferences_save = True
            
            bpy.data.scenes["Scene"].zen_uv.td_props.prp_current_td = get_td_value()
            bpy.data.scenes["Scene"].zen_uv.td_props.td_unit = get_td_unit()
            
            bpy.ops.wm.save_userpref()
            save_preferences.is_saving = False
    except Exception as e:
        print(f"Error saving preferences: {e}")
        save_preferences.is_saving = False


def get_td_value():
    """Get the texel density value from addon preferences"""
    try:
        preferences = bpy.context.preferences.addons[__name__].preferences
        value = preferences.zenuv_td_prop
        return value
    except Exception as e:
        print(e)
        return 10.0  # default value if preferences not found
    
def get_td_unit():
    """Get the texel density unit from addon preferences"""
    try:
        preferences = bpy.context.preferences.addons[__name__].preferences
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
    
    threshold = bpy.context.preferences.addons[__name__].preferences.clear_sharp_axis_float_prop
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
        selection_mode = tuple(bpy.context.scene.tool_settings.mesh_select_mode)
        
        # Store initial selections
        # Vertices
        selected_vertices = [v.index for v in mesh.vertices if v.select]
        
        # Edges
        selected_edges = [e.index for e in mesh.edges if e.select]
        
        # Faces
        selected_faces = [f.index for f in mesh.polygons if f.select]
        
        # Deselect all vertices
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT") # We're in Object mode so we can select stuff. Logic is weird.
        
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
        bpy.ops.object.mode_set(mode="EDIT")
        
        # Switch to edge mode
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type="EDGE")
        
        # Clear the Sharp
        bpy.ops.mesh.mark_sharp(clear=True)
        
        # Restore the inital selections and mode
        if selection_mode[0] is True:
            # Deselect all vertices
            bpy.ops.mesh.select_mode(type="VERT")
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.object.mode_set(mode="OBJECT") # We're in Object mode so we can select stuff. Logic is weird.
            for vert_idx in selected_vertices:
                mesh.vertices[vert_idx].select = True
        if selection_mode[1] is True:
            # Deselect all vertices
            bpy.ops.mesh.select_mode(type="EDGE")
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.object.mode_set(mode="OBJECT") # We're in Object mode so we can select stuff. Logic is weird.
            for edge_idx in selected_edges:
                mesh.edges[edge_idx].select = True
        if selection_mode[2] is True:
            # Deselect all vertices
            bpy.ops.mesh.select_mode(type="FACE")
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.object.mode_set(mode="OBJECT") # We're in Object mode so we can select stuff. Logic is weird.
            for face_idx in selected_faces:
                mesh.polygons[face_idx].select = True
        
        # Set back to Object mode
        bpy.ops.object.mode_set(mode=mode)

    
def iter_scene_objects(selected=False, type: str = ''):
        iters = bpy.data.objects
        if selected:
            iters = bpy.context.selected_objects
            
        for o in iters:
            if not type or o.type == type:
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
    bpy.ops.object.select_all(action="DESELECT")


class OP_ClearCustomData(bpy.types.Operator):
    bl_label = "Clear Split Normals"
    bl_idname = "r0tools.clear_custom_split_normals"
    bl_description = "Clears the Custom Split Normals assignments for selected objects and sets AutoSmooth to 180.\nUseful to quickly clear baked normals/shading assignments of multiple meshes at once."
    bl_options = {'REGISTER', 'UNDO'}
    
    def op_clear_custom_split_normals_data(self, objects):
        """
        Clears the Custom Split Normals assignments for selected objects and sets AutoSmooth to 180.
        
        Useful to quickly clear baked normals/shading assignments of multiple meshes at once.
        """
        
        if len(objects) != 0:
            orig_active = bpy.context.view_layer.objects.active
            for obj in objects:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
                # bpy.ops.object.shade_smooth() # Not needed. Will give an error if Weighted Normals modifier is present.
                bpy.context.object.data.use_auto_smooth = True
                bpy.context.object.data.auto_smooth_angle = 3.14159
            bpy.context.view_layer.objects.active = orig_active

    def execute(self, context):
        objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        self.op_clear_custom_split_normals_data(objects)
        show_notification("Custom Split Data cleared")
        return {'FINISHED'}

        
class OP_DissolveNthEdge(bpy.types.Operator):
    bl_label = "Remove Nth Edges"
    bl_idname = "r0tools.nth_edges"
    bl_description = "Remove Nth (every other) edges.\n\nUsage: Select 1 edge on each object and run the operation.\nNote: The selected edge and every other edge starting from it will be preserved.\n\nExpand Edges: Per default, the ring selection of edges expands to cover all connected edges to the ring selection. Turning it off will make it so that it only works on the immediate circular ring selection and will not expand to the continuous connected edges."
    bl_options = {'REGISTER', 'UNDO'}

    expand_edges: bpy.props.BoolProperty(name="Expand Edges", default=True)
    keep_initial_selection: bpy.props.BoolProperty(name="Keep Selected Edges", default=True)

    @classmethod
    def poll(cls, context):
        # Ensure at least one object is selected
        return any(obj.type == "MESH" and obj.select_get() for obj in context.selected_objects) and context.mode == "EDIT_MESH"

    def process_object(self, obj, context):
        # Make active
        context.view_layer.objects.active = obj

        if context.mode != "EDIT_MODE":
            bpy.ops.object.mode_set(mode="EDIT")
        
        # Create a bmesh
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.select_mode = {'EDGE'}

        # Currently selected edges
        initial_selection = [edge for edge in bm.edges if edge.select]

        # Edges to delete from all meshes
        edges_delete = []

        for i, edge in enumerate(initial_selection):
            print(f"{i} {edge.index}")
            
            # Deselect all bm edges
            for e in bm.edges:
                e.select = False

            # Select the original edge
            edge.select = True

            # Select the ring and nth
            bpy.ops.mesh.loop_multi_select(ring=True)
            bpy.ops.mesh.select_nth()

            selected_edges = [edge.index for edge in bm.edges if edge.select]
            if edge.index in selected_edges:
                # Deselect all bm edges
                for e in bm.edges:
                    e.select = False
                
                # Select the original edge
                edge.select = True
                bpy.ops.mesh.loop_multi_select(ring=True)
                bpy.ops.mesh.select_nth(offset=1)
            
            if self.expand_edges:
                bpy.ops.mesh.loop_multi_select(ring=False)

            # Store those edges
            edges_delete.extend([edge for edge in bm.edges if edge.select])

            # Deselect initial edge we want to keep
            edge.select = False

        # Make sure to deselect all bm edges too
        for e in bm.edges:
            e.select = False

        for edge in edges_delete:
            edge.select = True
        
        bpy.ops.mesh.dissolve_mode(use_verts=True)

        # Update the mesh
        bmesh.update_edit_mesh(me)
        bm.free()

        # Select initial selection of edges
        if self.keep_initial_selection:
            for edge in initial_selection:
                edge.select = True

    def execute(self, context):
        original_active_obj = context.active_object
        original_mode = context.mode

        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode="OBJECT")

        # Collect selected mesh objects
        selected_objects = [obj for obj in context.selected_objects if obj.type == "MESH"]
        # deselect_all()
        for obj in selected_objects:
            # obj.select_set(True)
            self.process_object(obj, context)
            # obj.select_set(False)

        # Return to the original active object and mode
        if original_mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode=original_mode)
        
        # Restore selection
        for obj in selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = original_active_obj

        return {'FINISHED'}
    

class OP_ApplyZenUVTD(bpy.types.Operator):
    bl_label = "Set TD"
    bl_idname = "r0tools.zenuv_set_td"
    bl_description = "Apply Texel Density from ZenUV to objects"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        context_mode = context.mode
        
        if context_mode not in ["OBJECT", "EDIT_MESH"]:
            self.report({'WARNING'}, "Only performed in Object or Edit modes")
            return {'CANCELLED'}
        
        selected_objs = list(iter_scene_objects(selected=True))
        active_obj = bpy.context.view_layer.objects.active
        
        if context_mode == "OBJECT":
            deselect_all()
        
        TD = get_td_value()
        TD_UNIT = get_td_unit()
        
        print(f"Setting TD {TD} for {len(selected_objs)} selected objects with {TD} px/{TD_UNIT}")
        
        bpy.data.scenes["Scene"].zen_uv.td_props.prp_current_td = TD
        bpy.data.scenes["Scene"].zen_uv.td_props.td_unit = TD_UNIT
        bpy.context.scene.zen_uv.td_props.td_set_mode = 'ISLAND'
        
        if context_mode == "OBJECT":
        
            for o in selected_objs:
                try:
                    print(f"Setting {TD} px/{TD_UNIT} for {o.name}")
                    
                    o.select_set(True)
                    
                    bpy.context.view_layer.objects.active = o
                    
                    bpy.context.view_layer.update()
                    
                    # Add a small delay to ensure the selection is registered
                    bpy.app.timers.register(lambda: None, first_interval=0.2)
                    
                    bpy.ops.uv.zenuv_set_texel_density(global_mode=True)
                    
                except Exception as e:
                    print(f"Error: {e}")
                    self.report({'ERROR'}, f"Error: {e}")
                    o.select_set(False)
                    
            for obj in selected_objs:
                obj.select_set(True)
                
            if active_obj:
                bpy.context.view_layer.objects.active = active_obj
        elif context_mode == "EDIT_MESH":
            # Add a small delay to ensure the selection is registered
            bpy.app.timers.register(lambda: None, first_interval=0.2)
            
            bpy.ops.uv.zenuv_set_texel_density(global_mode=True)
        
        self.report({'INFO'}, f"Texel density set to {TD} px/{TD_UNIT} for {len(selected_objs)} objects.")
        show_notification(f"Texel density set to {TD} px/{TD_UNIT} for {len(selected_objs)} objects.")
        
        return {'FINISHED'}


class OP_ClearMeshAttributes(bpy.types.Operator):
    bl_label = "Clear Attributes"
    bl_idname = "r0tools.clear_mesh_attributes"
    bl_description = "Clears unneeded mesh(es) attributes created by various addons.\nPreserves some integral and needed attributes such as material_index that is required for multi-material assignments.\nSometimes certain addons or operations will populate this list with attributes you wish to remove at a later date, be it for parsing or exporting."
    bl_options = {'REGISTER', 'UNDO'}
    
    def op_clear_mesh_attributes(self):
        """
        Clears unneeded mesh(es) attributes created by various addons. Preserves some integral and needed attributes such as material_index that is required for multi-material assignments.
        
        Sometimes certain addons or operations will populate this list with attributes you wish to remove at a later date, be it for parsing or exporting.
        """
        
        print(f"[CLEAR MESH ATTRIBUTES]")
        
        initial_obj = bpy.context.active_object
        
        exclude_filter = ("colorSet", "map", "material_index") # Starts with these tags
        attrs_check = (bpy.types.IntAttribute,
                       bpy.types.FloatAttribute,
                       bpy.types.FloatColorAttribute,
                       bpy.types.StringAttribute,
                       bpy.types.ByteColorAttribute,
                       bpy.types.FloatVectorAttribute,
                       bpy.types.FloatVectorAttributeValue
                       )
        
        for obj in bpy.context.selected_objects:
            if obj.type == "MESH":
                bpy.context.view_layer.objects.active = obj
                mesh = bpy.context.object.data
                print(f"Object: {mesh.name}")
                try:
                    for at in reversed(mesh.attributes.items()):
                        # Check if not T4 Attribute
                        if not isinstance(at[1], attrs_check):
                            continue
                        
                        at_name = at[0]
                        if str(at_name).startswith(exclude_filter):
                            print(f"{' '*2}Keeping Attribute: {at_name}")
                        else:                    
                            print(f"{' '*2}Removing Attribute: {at[0]}")
                            mesh.color_attributes.remove(at[1])
                except Exception as e:
                    print(e)
        
        bpy.context.view_layer.objects.active = initial_obj

    def execute(self, context):
        self.op_clear_mesh_attributes()
        return {'FINISHED'}
        
class OP_ClearChildrenRecurse(bpy.types.Operator):
    bl_label = "Clear Children"
    bl_idname = "r0tools.clear_all_objects_children"
    bl_description = "For each selected object, clears parenting keeping transform for each child object.\n(SHIFT): Recursively clears parenting for ALL object children and sub-children."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(obj.type == "MESH" and obj.select_get() for obj in context.selected_objects) and context.mode == "OBJECT"

    recurse: bpy.props.BoolProperty(default=False)
    
    def op_clear_all_objects_children(self, recurse=False):
        parent_objs = 0
        total_children_cleared = 0
        
        problem_objects = []
        
        active_obj = bpy.context.view_layer.objects.active
        
        # Match selected objects' data names to mesh names
        for o in iter_scene_objects(selected=True):
            print(f"Iter {o.name}")
            
            for child in iter_children(o, recursive=recurse):
                # print(f"Child: {child.name}")
                try:
                    self.process_child_object(child)
                    total_children_cleared += 1
                except Exception as e:
                    print(f"ERROR: {e}")
                    problem_objects.append(child)
            
            parent_objs += 1
                
        bpy.context.view_layer.objects.active = active_obj
        
        show_notification(f"Cleared {total_children_cleared} child objects for {parent_objs} main objects.")
        
        if problem_objects:
            deselect_all()
            for obj in problem_objects:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
                    child.hide_set(False)
                    child.hide_viewport = False
            show_notification(f"The following objects have raised issues: {', '.join([obj.name for obj in problem_objects])}")
        
    def process_child_object(self, child):
        """Handle visibility and selection state for a child object"""
        
        was_hidden = child.hide_get()
        was_hidden_viewport = child.hide_viewport
        
        if was_hidden:
            child.hide_set(False)
            
        if was_hidden_viewport:
            child.hide_viewport = False
        
        child.select_set(True)
        bpy.context.view_layer.objects.active = child
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        
        if was_hidden:
            child.hide_set(True)

        if was_hidden_viewport:
            child.hide_viewport = True

    def invoke(self, context, event):
        if event.shift:
            self.recurse = True
        else:
            self.recurse = False

        return self.execute(context)

    def execute(self, context):
        self.op_clear_all_objects_children(recurse=self.recurse)
        return {'FINISHED'}

class OP_CaptureObjectsScreenSizePct(bpy.types.Operator):
    bl_label = "Capture Visible"
    bl_idname = "r0tools.capture_screen_size_pct"
    bl_description = "Capture visible objects' screen size"
    bl_options = {'REGISTER'}

    polygon_threshold: bpy.props.FloatProperty(
        name="Screen Size Threshold (%)",
        default=1,
        min=0.0,
        max=100.0,
        description="Highlight meshes smaller than this screen size percentage"
    )

    def project_point(self, point, perspective_matrix, region):
        """
        Project a 3D point to 2D screen coordinates
        
        :param point: 3D input point
        :param perspective_matrix: 4x4 projection matrix
        :param region: Blender region
        :return: 2D screen coordinates or None if point is behind camera
        """
        # Convert point to 4D homogeneous coordinates
        point_4d = Vector((point.x, point.y, point.z, 1.0))
        
        # Apply projection matrix
        proj_point = perspective_matrix @ point_4d
        
        # Check if point is in front of the camera (w > 0)
        if proj_point.w > 1e-6:
            # Perspective divide
            ndc_point = proj_point.xyz / proj_point.w
            
            # Convert from normalized device coordinates to screen coordinates
            screen_x = (ndc_point.x * 0.5 + 0.5) * region.width
            screen_y = (ndc_point.y * 0.5 + 0.5) * region.height
            
            return (screen_x, screen_y)
        
        return None

    def execute(self, context):
        global highlight_faces
        highlight_faces = {} # Reset

        print(f"=== Capture Screen Size ===")

        # Collect select objects
        selected_objects = [obj for obj in bpy.context.selected_objects]
        original_active_obj = context.view_layer.objects.active

        # Get the current active area and region
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                region = area.regions[-1]  # Usually the main region
                break
        else:
            self.report({'ERROR'}, "Could not find 3D Viewport")
            return {'CANCELLED'}
        
        screen_space_objects = []
        total_screen_pct = 0.0

        # Get the current view matrix and projection matrix
        rv3d = bpy.context.space_data.region_3d
        projection_matrix = rv3d.perspective_matrix
        view_matrix = rv3d.view_matrix

        # Iterate through visible objects of specific types
        valid_types = {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}
        visible_objects = [
            obj for obj in bpy.context.visible_objects 
            if obj.type in valid_types
        ]

        total_screen_pct = 0
        
        for obj in visible_objects:
            # Calculate object's screen space
            screen_space_percentage = self.calculate_object_screen_space(obj, region, projection_matrix)
            screen_space_objects.append({
                'name': obj.name,
                'screen_space_percentage': screen_space_percentage
            })

            # total_screen_pct += min(screen_space_percentage, 100.0)
            if screen_space_percentage > total_screen_pct:
                total_screen_pct = screen_space_percentage

            # Analyze polygon screen space and create vertex groups
            self.analyze_polygon_screen_space(obj, region, self.polygon_threshold)

        # Ensure total screen percentage doesn't exceed 100%
        total_screen_pct = min(total_screen_pct, 100.0)

        # Print results
        self.report({'INFO'}, "Screen Space Analysis Complete")
        for obj_info in screen_space_objects:
            print(f"-> {obj_info['name']}: {obj_info['screen_space_percentage']:.2f}% screen space")

        # Set the scene property to the total screen percentage
        context.scene.screen_size_pct_prop = total_screen_pct

        # Restore selection
        for obj in selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = original_active_obj

        return {'FINISHED'}

    def calculate_object_screen_space_depr(self, obj, region):
        """
        Calculate the screen space percentage of an object.
        Approximates by projecting object's bounding box to screen.
        """
        context = bpy.context
        region_data = context.region_data
        
        # Get object's bounding box corners in world space
        bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        
        # Project 3D corners to 2D screen coordinates
        screen_corners = []
        for corner in bbox_corners:
            # Use region_data.view_matrix to project points
            view_coords = region_data.view_matrix @ corner
            
            # Perspective projection
            if view_coords.z != 0:
                x = (view_coords.x / -view_coords.z) * region.width / 2 + region.width / 2
                y = (view_coords.y / -view_coords.z) * region.height / 2 + region.height / 2
                screen_corners.append(Vector((x, y)))
        
        # Ensure we have enough corners to calculate area
        if len(screen_corners) < 3:
            return 0.0
        
        # Calculate total screen area and object's screen bbox area
        total_screen_area = region.width * region.height
        bbox_screen_area = self.calculate_polygon_area(screen_corners)

        screen_space_percentage = min((bbox_screen_area / total_screen_area) * 100, 100.0)
        print(f"{obj.name}: {screen_space_percentage}")
        
        return screen_space_percentage
    
    def calculate_object_screen_space(self, obj, region, perspective_matrix):
        # Get object's bounding box corners in world space
        bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        
        # Project 3D bbox corners to 2D screen space
        screen_points = []
        for corner in bbox_corners:
            screen_point = self.project_point(corner, perspective_matrix, region)
            if screen_point:
                screen_points.append(screen_point)

        print(f"{obj.name} {screen_points=}")

        # Compute screen space bounding box
        if screen_points:
            xs = [p[0] for p in screen_points]
            ys = [p[1] for p in screen_points]
            
            # Calculate bbox area
            bbox_width = max(xs) - min(xs)
            bbox_height = max(ys) - min(ys)
            screen_area = bbox_width * bbox_height
            
            # Calculate screen coverage percentage
            total_screen_area = region.width * region.height
            coverage_percentage = min((screen_area / total_screen_area) * 100, 100.0)
        else:
            coverage_percentage = 0.0
            
        return coverage_percentage

    def analyze_polygon_screen_space(self, obj, region, threshold):
        """
        Analyze individual polygon screen space and create vertex groups
        for polygons below the threshold.
        """
        # Ensure we have a mesh we can work with
        if obj.type != 'MESH':
            return

        # Create a new vertex group for low-screen-space polygons
        # If vertex group already exists, remove it first
        vg_name = f"{obj.name}_low_screen_space"
        vg = obj.vertex_groups.get(vg_name)
        if vg:
            obj.vertex_groups.remove(vg)
        # vg = obj.vertex_groups.new(name=f"{obj.name}_low_screen_space")
        
        # Create a bmesh for detailed polygon analysis
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.normal_update()

        total_screen_area = region.width * region.height
        low_screen_space_vertices = set()

        context = bpy.context
        region_data = context.region_data

        for face in bm.faces:
            # Project face vertices to screen
            face_screen_coords = []
            for vert in face.verts:
                world_pos = obj.matrix_world @ vert.co
                
                # Use view matrix for projection
                view_coords = region_data.view_matrix @ world_pos
                
                # Perspective projection
                if view_coords.z != 0:
                    x = (view_coords.x / -view_coords.z) * region.width / 2 + region.width / 2
                    y = (view_coords.y / -view_coords.z) * region.height / 2 + region.height / 2
                    face_screen_coords.append(Vector((x, y)))

            # Calculate screen space area of the face
            if len(face_screen_coords) >= 3:
                face_screen_area = self.calculate_polygon_area(face_screen_coords)
                face_screen_percentage = (face_screen_area / total_screen_area) * 100

                # If face is below threshold, add its vertices to vertex group
                if face_screen_percentage < threshold:
                    for vert in face.verts:
                        low_screen_space_vertices.add(vert.index)

        # Add vertices to vertex group
        # for vert_index in low_screen_space_vertices:
            # vg.add([vert_index], 1.0, 'ADD')

        bm.free()


    def calculate_polygon_area(self, points):
        """
        Calculate the area of a 2D polygon using shoelace formula.
        Works for arbitrary polygon shapes.
        """
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y
        return abs(area) / 2.0
    
class OP_ClearAxisSharpEdgesX(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_x"
    bl_description = "Clears sharp edges on the X axis."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        op_clear_sharp_along_axis('X')
        return {'FINISHED'}
    
class OP_ClearAxisSharpEdgesY(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_y"
    bl_description = "Clears sharp edges on the Y axis."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        op_clear_sharp_along_axis('Y')
        return {'FINISHED'}
    
class OP_ClearAxisSharpEdgesZ(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_z"
    bl_description = "Clears sharp edges on the Z axis."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        op_clear_sharp_along_axis('Z')
        return {'FINISHED'}

class PT_SimpleToolbox(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_quick_toolbox'
    bl_label = 'Quick Simple Toolbox'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    # bl_options = {"DEFAULT_CLOSED"}

    screen_size_pct_prop = bpy.props.FloatProperty(
        name="screen_size_pct_prop",
        default=0.0,
        min=0.0,
        max=100.0,
        subtype="PERCENTAGE"
    )

    def draw(self, context):
        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        layout = self.layout

        row = layout.row()
        row.prop(addon_prefs, "experimental_features", text="Experimental Features", icon="EXPERIMENTAL")
        
        row = layout.row()
        row.operator("script.reload", text="Reload Scripts", icon="NONE")
        
        # Object Ops
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Object Ops")
        row = box.row(align=True)
        row.operator("r0tools.clear_custom_split_normals")
        # row = box.row(align=True)
        # row.operator("r0tools.clear_mesh_attributes")
        row = box.row(align=True)
        row.operator("r0tools.clear_all_objects_children")
        row = box.row(align=True)
        
        # Mesh Ops
        # Clear Sharp Edges on Axis
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Mesh Ops")
        row = box.row(align=True)
        row.operator("r0tools.nth_edges")
        box = box.box()
        row = box.row(align=True)
        row.label(text="Clear Sharp Edges on Axis:")
        row = box.row(align=True)
        row.prop(addon_prefs, "clear_sharp_axis_float_prop", text="Threshold")
        row = box.row(align=True)
        row.scale_x = 5
        row.operator("r0tools.clear_sharp_axis_x", text="X")
        row.operator("r0tools.clear_sharp_axis_y", text="Y")
        row.operator("r0tools.clear_sharp_axis_z", text="Z")
        
        # TD Tools
        box = layout.box()
        row = box.row(align=True)
        row.label(text="ZenUV Texel Density")
        row = box.row(align=True)
        row.prop(addon_prefs, "zenuv_td_prop", text="TD:")
        row.prop(addon_prefs, "zenuv_td_unit_prop", text="Unit")
        row = box.row(align=True)
        row.operator("r0tools.zenuv_set_td")

        if addon_prefs.experimental_features:
            row = layout.row()
            row.label(text="EXPERIMENTAL", icon="EXPERIMENTAL")
            box = layout.box()
            row = box.row()
            row.label(text="LODs")
            row = box.row()
            row.operator("r0tools.capture_screen_size_pct")
            row = box.row()
            row.prop(context.scene, "screen_size_pct_prop", text="Screen Size (%):")
            # row.enabled = False


classes = [
    AddonPreferences,
    PT_SimpleToolbox,
    OP_ClearCustomData,
    OP_ClearMeshAttributes,
    OP_ClearChildrenRecurse,
    OP_ClearAxisSharpEdgesX,
    OP_ClearAxisSharpEdgesY,
    OP_ClearAxisSharpEdgesZ,
    OP_DissolveNthEdge,
    OP_ApplyZenUVTD,
    OP_CaptureObjectsScreenSizePct,
    OP_HighlightFacesGPU,
    OP_ClearGPUHighlights,
]

def register():
    bpy.types.Scene.screen_size_pct_prop = bpy.props.FloatProperty(
        name="Screen Size",
        description="Size",
        default=0.0,
        min=0.0
    )

    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
    