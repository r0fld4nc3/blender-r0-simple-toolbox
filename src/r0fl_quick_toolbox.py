import bpy
import math
import bmesh

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

# ============ ADDON PREFS =============
class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
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

    keep_initial_selection: bpy.props.BoolProperty(name="Keep Selected Edges", default=True)
    expand_edges: bpy.props.BoolProperty(name="Expand Edges", default=True)

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
    bl_idname = "r0tools.zenuv_td"
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
        
class MATERIAL_UL_matslots_example(bpy.types.UIList):
    # The draw_item function is called for each item of the collection that is visible in the list.
    #   data is the RNA object containing the collection,
    #   item is the current drawn item of the collection,
    #   icon is the "computed" icon for the item (as an integer, because some objects like materials or textures
    #   have custom icons ID, which are not available as enum items).
    #   active_data is the RNA object containing the active property for the collection (i.e. integer pointing to the
    #   active item of the collection).
    #   active_propname is the name of the active property (use 'getattr(active_data, active_propname)').
    #   index is index of the current item in the collection.
    #   flt_flag is the result of the filtering process for this item.
    #   Note: as index and flt_flag are optional arguments, you do not have to use/declare them here if you don't
    #         need them.
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = data
        slot = item
        ma = slot.material
        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # You should always start your row layout by a label (icon + text), or a non-embossed text field,
            # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
            # We use icon_value of label, as our given icon is an integer value, not an enum ID.
            # Note "data" names should never be translated!
            if ma:
                layout.prop(ma, "name", text="", emboss=False, icon_value=icon)
            else:
                layout.label(text="", translate=False, icon_value=icon)
        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class PT_SimpleToolbox(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_quick_toolbox'
    bl_label = 'Quick Simple Toolbox'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    # bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        addon_prefs = bpy.context.preferences.addons[__name__].preferences
        layout = self.layout
        
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
        row.operator("r0tools.zenuv_td")


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
]


def register():
    bpy.types.Object.action_list_index = bpy.props.IntProperty()
    for cls in classes:
        bpy.utils.register_class(cls)
    
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
    