import sys
import bpy
import math
import bmesh
import importlib

from .const import INTERNAL_NAME, DEBUG
from . import utils as u
from .properties import BoolProperty
from .uv_ops import select_small_uv_islands

# -------------------------------------------------------------------
#   MISC
# -------------------------------------------------------------------

# Store the original draw method BEFORE modifying it
_BUILTIN_ORIENTATIONS_PIE = bpy.types.VIEW3D_MT_orientations_pie
_ORIGINAL_ORIENTATIONS_PIE_DRAW = _BUILTIN_ORIENTATIONS_PIE.draw

def modified_orientations_pie_draw(self, context):
    """
    Modified draw method for the built-in Transform Orientations Pie Menu.

    Adds View More Operator and calls a custom Custom Transform Orientations Pie to show all Custom Transform Orientations.
    """

    # Call the stored original draw method directly
    _ORIGINAL_ORIENTATIONS_PIE_DRAW(self, context)

    len_custom_orientations = len(CustomTransformsOrientationsTracker.get_tracked_custom_orientations())
    if len_custom_orientations > 0:
        layout = self.layout
        pie = layout.menu_pie()
        pie.operator(
            "r0tools.show_custom_orientations_pie",
            text="View Custom",
            text_ctxt="Orientation",
        )


class CustomTransformsOrientationsTracker:
    # Class variable to store the list of custom orientations
    _custom_orientations = []
    _last_tracked_orientations = set()

    @classmethod
    @bpy.app.handlers.persistent
    def track_custom_orientations(cls, scene, context=None):
        """
        Persistent handler to monitor and track changes in custom transform orientations.
        
        :param scene: Current Blender scene
        :param context: Optional context
        """
        
        if DEBUG:
            print(f"------------- Track Custom Orientations -------------")

        try:
            # Attempt to extract current orientations
            current_orientations = cls.get_custom_transform_orientations()
            current_orientation_set = set(current_orientations)
            
            # Check for added orientations
            added_orientations = current_orientation_set - cls._last_tracked_orientations
            
            # Check for removed orientations
            removed_orientations = cls._last_tracked_orientations - current_orientation_set
            
            # Update if there are changes
            if added_orientations or removed_orientations:
                cls._custom_orientations = list(current_orientations)
                
                for orient in added_orientations:
                    if DEBUG:
                        print(f"[DEBUG] Custom Orientation Added: {orient}")
                
                for orient in removed_orientations:
                    if DEBUG:
                        print(f"[DEBUG] Custom Orientation Removed: {orient}")
                
                # Update the last tracked set
                cls._last_tracked_orientations = current_orientation_set
                
                # Update UI
                for area in bpy.context.screen.areas:
                    area.tag_redraw()
        except Exception as e:
            print(f"Error tracking custom orientations: {e}")
            u.context_error_debug(error=e)
    
    @classmethod
    def get_custom_transform_orientations(cls):
        return u.get_custom_transform_orientations()
    
    @classmethod
    def get_tracked_custom_orientations(cls):
        """
        Retrieve the list of tracked custom orientations.
        
        :return: List of custom orientation names
        """
        return cls._custom_orientations
    
    @classmethod
    def register_handler(cls):
        """
        Register the custom orientation tracking handler.
        """
        # Remove any existing handlers to prevent duplicates
        cls.unregister_handler()
        
        print(f"Registering Handler {cls.track_custom_orientations}")
        bpy.app.handlers.depsgraph_update_post.append(cls.track_custom_orientations)
        
        # Initial population of custom orientations
        cls._last_tracked_orientations = set(cls.get_custom_transform_orientations())
        cls._custom_orientations = list(cls._last_tracked_orientations)
    
    @classmethod
    def unregister_handler(cls):
        """
        Unregister the custom orientation tracking handler.
        """
        # Remove the handler if it exists
        if cls.track_custom_orientations in bpy.app.handlers.depsgraph_update_post:
            print(f"Unregistering Handler {cls.track_custom_orientations}")
            bpy.app.handlers.depsgraph_update_post.remove(cls.track_custom_orientations)


class TRANSFORM_OT_SetCustomOrientation(bpy.types.Operator):
    """
    Operator responsible for picking the chosen Custom Transform Orientations from the Custom Transform Orientations Menu
    """
    
    bl_label = "Set Custom Orientation"
    bl_idname = "r0tools.set_custom_orientation"
    bl_description = "Sets the picked Custom Transform Orientation"

    orientation: bpy.props.StringProperty(name="Orientation") # type: ignore

    def execute(self, context):
        # Reset the _invoked flag after selecting an orientation
        VIEW3D_MT_CustomOrientationsPieMenu._invoked = True

        try:
            if self.orientation in u.get_custom_transform_orientations():
                u.get_scene().transform_orientation_slots[0].type = self.orientation
            else:
                CustomTransformsOrientationsTracker.track_custom_orientations(bpy.context.scene)
                report_msg = f"Custom Transform Orientation '{self.orientation}' not found."
                self.report({'WARNING'}, report_msg)
                print(f"[WARN] {report_msg}")
            return {'FINISHED'}
        except Exception as err:
            report_msg = f"Could not set orientation: {err}"
            self.report({'ERROR'}, report_msg)
            print(f"[ERROR] Could not set orientation: {err}")
            u.context_error_debug(error=err)
            return {'CANCELLED'}


# -------------------------------------------------------------------
#   PIE MENUS
# -------------------------------------------------------------------
# Pie menus are arranged in the order West, East, South, North, Northwest, Northeast Southwest Southeast
class VIEW3D_MT_CustomOrientationsPieMenu(bpy.types.Menu):
    bl_label = "Custom Transform Orientations"
    bl_idname = "VIEW3D_MT_r0_custom_orientations_pie"

    _current_start_index = 0
    _invoked = True
    _VALID_CONTEXTS = [u.AREA_TYPES.VIEW_3D]

    @classmethod
    def poll(cls, context):
        if u.get_context_area() not in cls._VALID_CONTEXTS:
            print(f"Not drawing Custom Transform Orientations Pie: '{u.get_context_area()} not in valid context areas: {cls._VALID_CONTEXTS}")
            return False
        return True
    
    @classmethod
    def reset(cls):
        """Reset relevant class flags"""
        cls._current_start_index = 0
        cls._invoked = True

    def draw(self, context):
        print("Draw Custom Transform Orientations Pie Menu")
        layout = self.layout
        pie = layout.menu_pie()

        # Reset index if never called or coming from a different context
        if self.__class__._invoked:
            self.__class__.reset()

        custom_orientations = CustomTransformsOrientationsTracker.get_tracked_custom_orientations()

        # Calulate range of items to display
        remaining_orientations = len(custom_orientations) - self._current_start_index
        start_index = self._current_start_index
        end_index = min(start_index + 8, len(custom_orientations))

        if DEBUG:
            print(f"[DEBUG] {remaining_orientations=}")
            print(f"[DEBUG] {start_index=}")
            print(f"[DEBUG] {end_index=}")

        total_added = 0 # 8 is the maximum allowed
        for orientation_name in custom_orientations[self.__class__._current_start_index:]:
            # Add custom transform to pie menu as an operator if not exceptions raised
            try:
                op = pie.operator(
                    "r0tools.set_custom_orientation",
                    text=orientation_name,
                    text_ctxt="Orientation",
                )
                # op.bl_description = f"Sets the > {orientation_name} < Custom Transform Orientation"
                op.orientation = orientation_name
                
                # Update iterations
                total_added += 1
                if DEBUG:
                    print(f"[DEBUG] ({self.__class__._current_start_index}) {orientation_name}")
            except Exception as err:
                print(f"Error adding Custom Orientation to Pie Menu: {err}")
                u.context_error_debug(error=err)

            # "View More" if there are additional orientations
            if total_added == 7 and remaining_orientations > 8:
                try:
                    op = pie.operator(
                        "wm.call_menu_pie",
                        text="View More",
                        text_ctxt="Orientation"
                    )
                    op.name = "VIEW3D_MT_r0_custom_orientations_pie"
                    
                    # Store the next starting index for the next call
                    # Compensate for now showing last entry with -1, so index starts at missing entry from this round
                    self.__class__._current_start_index = end_index - 1
                    # Ensure we're not treating it as invoked
                    self.__class__._invoked = False

                    # Update iterations
                    total_added += 1
                    if DEBUG:
                        print(f"[DEBUG] ({self.__class__._current_start_index}) {orientation_name}")
                except Exception as err:
                    print(f"Error adding View More to Pie Menu: {err}")
                    u.context_error_debug(error=err)

            # Break the fill loop if we've successfully filled 8 entries
            if total_added >= 8:
                if DEBUG:
                    print(f"[DEBUG] Menu entries limit reached! Total added: {total_added}")
                break


class SimpleToolbox_OT_ShowCustomOrientationsPie(bpy.types.Operator):
    """
    Operator that is responsible for calling the Pie Menu.
    """
    
    bl_label = "Show Custom Transform Orientations Pie Menu"
    bl_idname = "r0tools.show_custom_orientations_pie"
    bl_description = "Show a pie menu with a maximum of 8 custom transform orientations"

    def execute(self, context):
        # Reset the _invoked flag after selecting an orientation
        VIEW3D_MT_CustomOrientationsPieMenu._invoked = True

        bpy.ops.wm.call_menu_pie(name="VIEW3D_MT_r0_custom_orientations_pie")
        return {'FINISHED'}


# -------------------------------------------------------------------
#   EXPERIMENTAL
# -------------------------------------------------------------------
class SimpleToolbox_OT_ExperimentalOP(bpy.types.Operator):
    bl_label = "Exp Op 1"
    bl_idname = "r0tools.experimental_op_1"
    bl_description = ""
    bl_options = {'REGISTER'}

    def get_viewport(self, context):
        # Get the active 3D viewport
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                # Get the region and region 3D view
                region = None
                rv3d = None
                for r in area.regions:
                    if r.type == 'WINDOW':
                        region = r
                        break
                rv3d = area.spaces[0].region_3d
                
                # Exit the loop once we find a valid viewport
                break
        
        # Validate viewport
        if not (region and rv3d):
            self.report({'ERROR'}, "Could not find 3D viewport")
            return (None, None)
        
        return region, rv3d
    
    def get_loose_vertices(self, obj):
        obj_verts = [v.index for v in obj.data.vertices]
        loop_verts = [] # Vertices which are part of a loop
        loose_verts = []

        # bpy.ops.mesh.select_non_manifold() # Requires Edit Mode
        
        for p in obj.data.polygons:
            poly_idx = p.index
            poly_verts = [p.vertices[0], p.vertices[1], p.vertices[2]]
            loop_verts.append(poly_verts)

            print(f"P{poly_idx}: {poly_verts}")
            
        for v in obj_verts:
            found = False
            for vert_loop in loop_verts:
                if v in vert_loop:
                    found = True
                    break

            if not found:
                loose_verts.append(v)

        if loose_verts:
            print(f"{obj.name} has {len(loose_verts)} loose vertices: {loose_verts}")

        return loose_verts

    def execute(self, context):
        print("\n------------- Experimental Operator 1 -------------")
        region, rv3d = self.get_viewport(context)

        # Get the actual viewport dimensions
        viewport_width = region.width
        viewport_height = region.height
        viewport_diagonal = math.sqrt(viewport_width**2 + viewport_height**2)

        print(f"Viewport WxH: {viewport_width}x{viewport_height}")

        orig_active = context.view_layer.objects.active
        
        visible_objects = [o for o in u.iter_scene_objects() if o.visible_get()]

        for o in visible_objects:
            self.get_loose_vertices(o)

        context.view_layer.objects.active = orig_active

        return {'FINISHED'}


# -------------------------------------------------------------------
#   DEV OPS
# -------------------------------------------------------------------
class SimpleToolbox_OT_ReloadNamedScripts(bpy.types.Operator):
    bl_label = "Reload Script(s)"
    bl_idname = "r0tools.reload_named_scripts"
    bl_description = "Reload only specified scripts from a name text box."
    bl_options = {'REGISTER'}

    def get_input_modules(self) -> list[str]:
        text = u.get_addon_props().reload_modules_prop
        modules = []
        if text:
            modules.extend([t.strip() for t in text.split(',')])
        
        return modules
    
    def reload_module(self, mod_name) -> bool:
        try:
            # Check if the module is already imported
            if mod_name in sys.modules:
                # Reload the module
                module = sys.modules[mod_name]
                importlib.reload(module)
                
                # If it's an addon, re-register its classes
                if hasattr(module, 'register'):
                    try:
                        module.unregister()
                    except Exception as unreg_err:
                        print(f"Error unregistering {mod_name}: {unreg_err}")
                    
                    try:
                        module.register()
                    except Exception as reg_err:
                        print(f"Error re-registering {mod_name}: {reg_err}")
                
                print(f"Reloaded {mod_name}")
                return True
            else:
                print(f"Module {mod_name} not found in sys.modules")
                return False
        except Exception as e:
            print(f"Error reloading {mod_name}: {e}")
            return False

    def execute(self, context):
        print("\n------------- Reload Named Scripts -------------")
        modules = self.get_input_modules()

        if not modules:
            modules.append(INTERNAL_NAME)

        failures = []
        successes = []
        if modules:
            for module in modules:
                try:
                    success = self.reload_module(module)
                except Exception as e:
                    print(e)
                    success = False
                if success:
                    successes.append(module)
                else:
                    failures.append(module)
        
        print(f"Reloaded: {successes}")
        print(f"Failed: {failures}")

        reload_msg = f"Reloaded {len(successes)}. Unable to reload {len(failures)}"
        
        try:
            self.report({'INFO'}, reload_msg)
        except Exception as e:
            print(f"Error reporting results: {e}")
        
        u.show_notification(reload_msg)
        
        return {'FINISHED'}
    

# -------------------------------------------------------------------
#   OBJECT OPS
# -------------------------------------------------------------------
class SimpleToolbox_OT_ClearCustomSplitNormalsData(bpy.types.Operator):
    bl_label = "Clear Split Normals"
    bl_idname = "r0tools.clear_custom_split_normals_data"
    bl_description = "Clears the Custom Split Normals assignments for selected objects and sets AutoSmooth to 180.\nUseful to quickly clear baked normals/shading assignments of multiple meshes at once."
    bl_options = {'REGISTER', 'UNDO'}
    
    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0
    
    def op_clear_custom_split_normals_data(self, objects):
        """
        Clears the Custom Split Normals assignments for selected objects and sets AutoSmooth to 180.
        
        Useful to quickly clear baked normals/shading assignments of multiple meshes at once.
        """
        
        for obj in objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            bpy.ops.object.shade_smooth()
            # bpy.ops.object.shade_smooth() # Not needed. Will give an error if Weighted Normals modifier is present.
            # bpy.context.object.data.use_auto_smooth = True
            # bpy.context.object.data.auto_smooth_angle = 3.14159

    def execute(self, context):
        print("\n------------- Clear Custom Split Normals Data -------------")
        orig_context = context.mode
        orig_active = bpy.context.view_layer.objects.active

        if context.mode == u.OBJECT_MODES.EDIT_MESH:
            u.set_mode_object()

        objects = [obj for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH])]
        self.op_clear_custom_split_normals_data(objects)
        bpy.context.view_layer.objects.active = orig_active

        if orig_context != u.OBJECT_MODES.OBJECT and orig_context == u.OBJECT_MODES.EDIT_MESH:
            u.set_mode_edit()

        msg = f"Finished clearing Custom Split Data across {len(objects)} objects"
        # u.show_notification(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class SimpleToolbox_OT_ClearCustomProperties(bpy.types.Operator):
    bl_label = "Delete"
    bl_idname = "r0tools.delete_custom_properties"
    bl_description = "Delete Custom Properties from Object(s)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        print("\n------------- Clear Custom Properties -------------")
        object_data_property_deletions = set()
        mesh_data_property_deletions = set()
        total_deletions = 0
        total_objects = 0
        
        # Find selected properties to remove
        props_to_remove = [
            item for item in u.get_addon_props().custom_property_list 
            if item.selected
        ]

        for obj in context.selected_objects:    
            # Remove selected properties
            for custom_prop in props_to_remove:
                prop_name = custom_prop.name
                prop_type = custom_prop.type

                # Object Data
                if prop_type == u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA:
                    if prop_name in reversed(obj.keys()):
                        print(f"Deleting Object Data Property '{prop_name}' of object {obj.name}")
                        del obj[prop_name]
                        object_data_property_deletions.add(prop_name)
                        total_objects += 1
                # Mesh Data
                elif prop_type == u.CUSTOM_PROPERTIES_TYPES.MESH_DATA:
                    if prop_name in reversed(obj.data.keys()):
                        print(f"Deleting Mesh Data Property '{prop_name}' of object {obj.name}")
                        del obj.data[prop_name]
                        mesh_data_property_deletions.add(prop_name)
                        total_objects += 1
        
        total_deletions = len(object_data_property_deletions) + len(mesh_data_property_deletions)
        
        # u.show_notification(f"Deleted {total_deletions} propertie(s) across {total_objects} object(s)")
        self.report({'INFO'}, f"Deleted {total_deletions} propertie(s) across {total_objects} object(s)")
        return {'FINISHED'}
     

class SimpleToolbox_OT_ClearMeshAttributes(bpy.types.Operator):
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
            if obj.type == u.OBJECT_TYPES.MESH:
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
                    print(f"[ERROR] Error Clearing Mesh Attributes")
                    u.context_error_debug(error=e)
        
        bpy.context.view_layer.objects.active = initial_obj

    def execute(self, context):
        print("\n------------- Clear Mesh Attributes -------------")
        self.op_clear_mesh_attributes()
        return {'FINISHED'}


class SimpleToolbox_OT_ClearChildrenRecurse(bpy.types.Operator):
    bl_label = "Clear Children"
    bl_idname = "r0tools.clear_all_objects_children"
    bl_description = "For each selected object, clears parenting keeping transform for each child object.\n\n- SHIFT: Recursively clears parenting for ALL object children and sub-children."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH])) and context.mode == u.OBJECT_MODES.OBJECT

    recurse: BoolProperty(name="Recursively clear all children", default=False) # type: ignore
        
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
        self.recurse = False # Always reset

        if event.shift:
            self.recurse = True

        return self.execute(context)

    def execute(self, context):
        print("\n------------- Clear Object(s) Children -------------")
        parent_objs = 0
        total_children_cleared = 0
        
        problem_objects = []
        
        active_obj = bpy.context.view_layer.objects.active
        
        # Match selected objects' data names to mesh names
        for o in u.iter_scene_objects(selected=True):
            print(f"Iter {o.name}")
            
            for child in u.iter_children(o, recursive=self.recurse):
                # print(f"Child: {child.name}")
                try:
                    self.process_child_object(child)
                    total_children_cleared += 1
                except Exception as e:
                    print(f"ERROR: {e}")
                    u.context_error_debug(error=e)
                    problem_objects.append(child)
            
            parent_objs += 1
                
        bpy.context.view_layer.objects.active = active_obj
        
        cleared_msg = f"Cleared {total_children_cleared} child objects for {parent_objs} main objects."
        # u.show_notification(cleared_msg)
        self.report({'INFO'}, cleared_msg)
        
        if problem_objects:
            u.deselect_all()
            for obj in problem_objects:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
                    child.hide_set(False)
                    child.hide_viewport = False
            issues_msg = f"The following objects have raised issues: {', '.join([obj.name for obj in problem_objects])}"
            u.show_notification(issues_msg)
            self.report({'WARNING'}, issues_msg)
        
        return {'FINISHED'}
    

class SimpleToolbox_OT_FindModifierSearch(bpy.types.Operator):
    bl_idname = "r0tools.find_modifier_search"
    bl_label = "Find Modifiers"
    bl_description = "Find and select objects whose modifier name(s) or type(s) match the given search text criteria.\nTo search for a mix of name and type and/or multiple criteria, use a comma-separated string, ex.: \"!!, weld, nodes\"\nNote: Case Insensitive\n\n- SHIFT: Add to selection"
    bl_options = {'REGISTER', 'UNDO'}

    add_to_selection: BoolProperty(default=False, name="Add To Selection") # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT

    def invoke(self, context, event):
        self.add_to_selection = False # Always reset

        if event.shift:
            self.add_to_selection = True

        return self.execute(context)

    def execute(self, context):
        addon_props = u.get_addon_props()

        print("\n------------- Find Modifier(s) Search -------------")

        search_text = addon_props.find_modifier_search_text.lower()
        search_text_split = [s.strip() for s in search_text.split(",")]
        
        view_layer_objs = bpy.context.view_layer.objects
        scene_objects = bpy.context.scene.objects

        if DEBUG:
            print(f"[DEBUG] {search_text=}")
            print(f"[DEBUG] (FLAG) {self.add_to_selection=}")

        if not self.add_to_selection:
            active_object = None
        else:
            active_object = context.active_object

        if DEBUG:
            print(f"[DEBUG] {active_object=}")

        if not self.add_to_selection:
            u.deselect_all()
        
        for obj in view_layer_objs:
            if not u.object_visible(obj):
                continue
            
            is_found = False
            obj_modifiers = obj.modifiers

            for modifier in obj_modifiers:
                mod_name = modifier.name
                mod_type = modifier.type

                for search_term in search_text_split:
                    if is_found:
                        break
                    if search_term in mod_name.lower() or search_text in mod_type.lower():
                        if DEBUG:
                            print(f"{search_term} in {mod_name} or {mod_type}")

                        if not self.add_to_selection:
                            if not active_object:
                                active_object = obj
                                u.select_object(obj, set_active=True)
                                is_found = True
                            else:
                                u.select_object(obj)
                                is_found = True
                        else:
                            if not active_object:
                                active_object = obj
                                u.select_object(obj, set_active=True)
                                is_found = True
                            else:
                                u.select_object(obj)
                                is_found = True

                        break

        return {'FINISHED'}
    

class SimpleToolbox_OT_ObjectSetsModal(bpy.types.Operator):
    bl_idname = "r0tools.object_sets_modal"
    bl_label = "Object Sets Modal"

    def invoke(self, context, event):
        object_sets_modal_prefs_width = u.get_addon_prefs().object_sets_modal_width
        return context.window_manager.invoke_props_dialog(self, width=object_sets_modal_prefs_width)
    
    def execute(self, context):
        return {'FINISHED'}
    
    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':  # Ignore mouse movement events
            return {'PASS_THROUGH'}

        if event.type in {"ESC", "RIGHTMOUSE"}:
            return {'CANCELLED'}
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if context.window_manager.dialog_properties.is_property_set("clicked"):
                if context.window_manager.dialog_properties.clicked == 'OK':
                    return {'FINISHED'}
                elif context.window_manager.dialog_properties.clicked == 'CANCEL':
                    return {'CANCELLED'}

        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        u.draw_objects_sets_uilist(self.layout, context, object_sets_box=self.layout)
    

class SimpleToolbox_OT_AddObjectSetPopup(bpy.types.Operator):
    bl_label = "+"
    bl_idname = "r0tools.add_object_set_popup"
    bl_description = "Add a new Object Set Entry."
    bl_options = {'REGISTER', 'UNDO'}

    _default_name = "New Set"
    object_set_name: bpy.props.StringProperty(name="Set Name", default=_default_name) # type: ignore

    def invoke(self, context, event):
        # Reset Name
        self.object_set_name = self._default_name
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def add_non_conflicting_name(self) -> str:
        addon_props = u.get_addon_props()
        existing_names = [object_set.name for object_set in addon_props.object_sets]

        if self.object_set_name not in existing_names:
            return self.object_set_name
        
        # Base name without suffix
        base_prefix = self.object_set_name.split('.')[0]
        
        # Collect all existing suffixes for this base name
        used_suffixes = set()
        for name in existing_names:
            if name.startswith(base_prefix):
                # Try to extract the numerical suffix
                parts = name.split('.')
                if len(parts) > 1:
                    try:
                        suffix = int(parts[-1])
                        used_suffixes.add(suffix)
                    except ValueError:
                        # Ignore names without valid numerical suffixes
                        pass
        
        # Lowest available suffix
        suffix = 1
        while suffix in used_suffixes:
            suffix += 1
        
        return f"{self.object_set_name}.{suffix:03}"

    def execute(self, context):
        addon_props = u.get_addon_props()
        new_set = addon_props.object_sets.add()
        new_set.name = self.add_non_conflicting_name()
        addon_props.object_sets_index = len(addon_props.object_sets) - 1

        # Immediately add selected objects to set, for convenience
        if context.selected_objects:
            bpy.ops.r0tools.add_to_object_set()

        if context.area:
            context.area.tag_redraw()

        self.report({'INFO'}, f"Created Object Set: {self.object_set_name}")
        return {'FINISHED'}
    

class SimpleToolbox_OT_RenameObjectSet(bpy.types.Operator):
    bl_label = "Rename"
    bl_idname = "r0tools.rename_object_set"
    bl_description = "Rename the selected Object Set entry."

    new_name: bpy.props.StringProperty(name="New Object Set Name", default="") # type: ignore

    def invoke(self, context, event):
        addon_props = u.get_addon_props()
        index = addon_props.object_sets_index

        if 0 <= index < len(addon_props.object_sets):
            object_set = addon_props.object_sets[index]
            self.new_name = object_set.name

        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        # Update cleanup dangling references
        # u.handler_cleanup_object_set_invalid_references(context)

        addon_props = u.get_addon_props()
        index = addon_props.object_sets_index

        if 0 <= index < len(addon_props.object_sets):
            object_set = addon_props.object_sets[index]
            old_name = object_set.name
            object_set.name = self.new_name
            self.report({'INFO'}, f"Renamed '{old_name}' to '{self.new_name}'")

        return {'FINISHED'}

class SimpleToolbox_OT_RemoveObjectSet(bpy.types.Operator):
    bl_label = "-"
    bl_idname = "r0tools.remove_object_set"
    bl_description = "Remove the selected Object Set entry."
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return len(u.get_addon_props().object_sets) > 0

    def execute(self, context):
        # Update cleanup dangling references
        # u.handler_cleanup_object_set_invalid_references(context)

        addon_props = u.get_addon_props()
        index = addon_props.object_sets_index

        if 0 <= index < len(addon_props.object_sets):
            set_name = addon_props.object_sets[index].name
            addon_props.object_sets.remove(index)
            addon_props.object_sets_index = max(0, index - 1)
            self.report({'INFO'}, f"Removed Object Set: {set_name}")
        return {'FINISHED'}
    

class SimpleToolbox_OT_MoveObjectSetItemUp(bpy.types.Operator):
    bl_label = "Move Object Set Up"
    bl_idname = "r0tools.move_object_set_item_up"
    bl_description = "Move the selected Object Set up.\n\n- SHIFT: Move to Top"
    bl_options = {'INTERNAL'}

    absolute: BoolProperty(default=False) # type: ignore

    def invoke(self, context, event):
        self.absolute = False # Always reset

        if event.shift:
            self.absolute = True

        return self.execute(context)

    def execute(self, context):
        addon_props = u.get_addon_props()
        object_sets = addon_props.object_sets
        active_index = addon_props.object_sets_index

        if active_index > 0:
            if self.absolute:
                to_index = 0 # All the way down
            else:
                to_index = active_index - 1

            object_sets.move(active_index, to_index)
            addon_props.object_sets_index = to_index
            addon_props.object_sets[active_index].update_count()
            addon_props.object_sets[to_index].update_count()

        return {'FINISHED'}
    

class SimpleToolbox_OT_MoveObjectSetItemDown(bpy.types.Operator):
    """Move the active Object Set down in the list"""
    bl_label = "Move Object Set Down"
    bl_idname = "r0tools.move_object_set_item_down"
    bl_description = "Move the selected Object Set down.\n\n- SHIFT: Move to Bottom"
    bl_options = {'INTERNAL'}

    absolute: BoolProperty(default=False) # type: ignore

    def invoke(self, context, event):
        self.absolute = False # Always reset

        if event.shift:
            self.absolute = True

        return self.execute(context)

    def execute(self, context):
        addon_props = u.get_addon_props()
        object_sets = addon_props.object_sets
        active_index = addon_props.object_sets_index

        if active_index < len(object_sets) - 1:
            if self.absolute:
                to_index = len(object_sets) - 1 # All the way down
            else:
                to_index = active_index + 1
            
            object_sets.move(active_index, to_index)
            addon_props.object_sets_index = to_index
            addon_props.object_sets[active_index].update_count()
            addon_props.object_sets[to_index].update_count()

        return {'FINISHED'}


class SimpleToolbox_OT_AddToObjectSet(bpy.types.Operator):
    bl_label = "Add"
    bl_idname = "r0tools.add_to_object_set"
    bl_description = "Add selected objects to selected Object Set Entry."
    bl_options = {'REGISTER'}

    accepted_contexts = [u.OBJECT_MODES.OBJECT]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        # Update cleanup dangling references
        # u.handler_cleanup_object_set_invalid_references(context)

        addon_props = u.get_addon_props()
        index = addon_props.object_sets_index

        if 0 <= index < len(addon_props.object_sets):
            object_set = addon_props.object_sets[index]

            for obj in context.selected_objects:
                object_set.add_object(obj)

            self.report({'INFO'}, f"Added {len(context.selected_objects)} objects to Set '{object_set.name}'")
        return {'FINISHED'}
    

class SimpleToolbox_OT_RemoveFromObjectSet(bpy.types.Operator):
    bl_label = "Remove"
    bl_idname = "r0tools.remove_from_object_set"
    bl_description = "Remove selected objects from selected Object Set entry."
    bl_options = {'REGISTER'}

    accepted_contexts = [u.OBJECT_MODES.OBJECT]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        # Update cleanup dangling references
        # u.handler_cleanup_object_set_invalid_references(context)

        addon_props = u.get_addon_props()
        index = addon_props.object_sets_index

        total_removed = 0

        if 0 <= index < len(addon_props.object_sets):
            object_set = addon_props.object_sets[index]

            for obj in context.selected_objects:
                print(f"{obj.name} in {[o.name for o in context.selected_objects]}")
                object_set.remove_object(obj)
                total_removed += 1

            self.report({'INFO'}, f"Removed {total_removed} objects of Set '{object_set.name}'")
        return {'FINISHED'}
    

class SimpleToolbox_OT_SelectObjectSet(bpy.types.Operator):
    bl_label = "Select"
    bl_idname = "r0tools.select_object_set"
    bl_description = "SHIFT: Add to Selection"
    bl_options = {'REGISTER'}

    add_to_selection = False

    accepted_contexts = accepted_contexts = [u.OBJECT_MODES.OBJECT]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts

    def invoke(self, context, event):
        self.add_to_selection = False # Always reset

        if event.shift:
            self.add_to_selection = True

        return self.execute(context)

    def execute(self, context):
        # Update cleanup dangling references
        # u.handler_cleanup_object_set_invalid_references(context)

        addon_props = u.get_addon_props()
        index = addon_props.object_sets_index

        if 0 <= index < len(addon_props.object_sets):
            object_set = addon_props.object_sets[index]
            
            if DEBUG:
                print(f"{self.add_to_selection=}")

            if not self.add_to_selection:
                u.deselect_all()

            to_become_active = None
            for item in reversed(object_set.objects):
                obj = item.object
                if not u.select_object(obj):
                    object_set.remove_object(obj)
                else:
                    # Set active object
                    if not self.add_to_selection and not to_become_active:
                        to_become_active = obj

            # Set active object if not adding to selection
            if not self.add_to_selection:
                u.set_active_object(to_become_active)

            self.report({'INFO'}, f"Selected objects in '{object_set.name}'")
        return {'FINISHED'}

# -------------------------------------------------------------------
#   MESH OPS
# -------------------------------------------------------------------
class SimpleToolbox_OT_DissolveNthEdge(bpy.types.Operator):
    bl_label = "Remove Nth Edges"
    bl_idname = "r0tools.nth_edges"
    bl_description = "Remove Nth (every other) edges from edge loops.\nSelect one edge per disconnected mesh to define the starting point.\n\nBy default, the selection automatically expands to include all connected edges in the loop. To limit the operation to only the manually selected contiguous edges or restrict it to the original ring selection, disable 'Expand Edges.'"
    bl_options = {'REGISTER', 'UNDO'}

    expand_edges: BoolProperty(name="Expand Edges", default=True) # type: ignore
    keep_initial_selection: BoolProperty(name="Keep Selected Edges", default=True) # type: ignore

    @classmethod
    def poll(cls, context):
        # Ensure at least one object is selected
        return any(u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH])) and context.mode == u.OBJECT_MODES.EDIT_MESH

    def process_object(self, obj, context):
        # Make active
        u.set_active_object(obj)

        if context.mode != u.OBJECT_MODES.EDIT_MESH:
            u.set_mode_edit()
        
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
        print("\n------------- Dissolve Nth Edges -------------")
        original_active_obj = context.active_object
        original_mode = context.mode

        if original_mode != u.OBJECT_MODES.OBJECT:
            u.set_mode_object()

        # Collect selected mesh objects
        selected_objects = [obj for obj in context.selected_objects if obj.type == u.OBJECT_TYPES.MESH]
        for obj in selected_objects:
            self.process_object(obj, context)

        # Return to the original active object and mode
        if original_mode != u.OBJECT_MODES.EDIT_MESH:
            bpy.ops.object.mode_set(mode=original_mode)
            u.set_object_mode(original_mode)
        
        # Restore selection
        for obj in selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = original_active_obj

        return {'FINISHED'}
    

class SimpleToolbox_OT_RestoreRotationFromSelection(bpy.types.Operator):
    bl_label = "Restore Rotation"
    bl_idname = "r0tools.rotation_from_selection"
    bl_description = "Given a selection of vertices/edges/faces, align each object such that the selection aligns to the Z Axis.\n\n- SHIFT: Clear object rotations on finish. (Also present in Redo panel)."
    bl_options = {'REGISTER', 'UNDO'}

    clear_rotation_on_align: BoolProperty(name="Clear Rotation(s)", default=False) # type: ignore
    origin_to_selection: BoolProperty(name="Origin to selection", default=False) # type: ignore
    keep_original_tool_configs: BoolProperty(name="Restore Tool Configurations", default=True) # type: ignore

    @classmethod
    def poll(cls, context):
        return any(u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH])) and context.mode == u.OBJECT_MODES.EDIT_MESH
    
    def invoke(self, context, event):
        self.clear_rotation_on_align = False # Always reset
        self.origin_to_selection = False # Always reset

        if event.shift:
            self.clear_rotation_on_align = True

        return self.execute(context)
    
    def execute(self, context):
        print("\n------------- Restore Rotation From Selection -------------")
        # Store original configurations
        orig_affect_only_origins = u.get_scene().tool_settings.use_transform_data_origin
        orig_affect_only_locations = u.get_scene().tool_settings.use_transform_pivot_point_align
        orig_affect_only_parents = u.get_scene().tool_settings.use_transform_skip_children
        orig_transform_orientation = u.get_scene().transform_orientation_slots[0].type
        orig_cursor_location = tuple(u.get_scene().cursor.location.xyz)
        orig_cursor_rotation = tuple(u.get_scene().cursor.rotation_euler)
        orig_active_obj = context.active_object
        orig_selected_objects = list(u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]))
        
        transform_orientation_names = []
        
        for obj in orig_selected_objects:
            print(f"Iterating Object: {obj.name}")
            u.select_object(obj, add=False, set_active=True)
            u.set_mode_edit()

            # TODO: Check for selected loops/polygons, otherwise, skip.

            # Create Transform Orientation
            to_name = f"{obj.name}_restore_orientation"
            transform_orientation_names.append(to_name)
            bpy.ops.transform.create_orientation(name=to_name, use=True) # Immediately set to use it

            u.set_mode_object()

            # Affect only origins
            u.get_scene().tool_settings.use_transform_data_origin = True
            u.get_scene().tool_settings.use_transform_pivot_point_align = False
            u.get_scene().tool_settings.use_transform_skip_children = False

            # Align to Transform Orientation
            bpy.ops.transform.transform(mode='ALIGN')

            # Clear affect only origins
            u.get_scene().tool_settings.use_transform_data_origin = False

            # Conditionally clear rotations based on property
            if self.clear_rotation_on_align:
                print(f"Clearing Rotation for {obj.name}")
                obj.rotation_euler = (0, 0, 0)
            else:
                print(f"Keeping Rotation for {obj.name}")

            # Check if we're just setting origin to transform
            if self.origin_to_selection:
                u.set_mode_edit()
                print(f"Setting object origin to median of selection for {obj.name}")
                bpy.ops.view3d.snap_cursor_to_selected()
                u.set_mode_object()
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

        # Restore selection
        for obj in orig_selected_objects:
            u.select_object(obj) # Add to selection
            u.set_mode_edit()
        
        # Restore active object
        u.set_active_object(orig_active_obj)

        # Delete custom orientations
        for orientation_name in transform_orientation_names:
            u.delete_custom_transform_orientation(orientation_name)

        # Restore effectors and transform orientation selections
        if self.keep_original_tool_configs:
            u.get_scene().tool_settings.use_transform_data_origin = orig_affect_only_origins
            u.get_scene().tool_settings.use_transform_pivot_point_align = orig_affect_only_locations
            u.get_scene().tool_settings.use_transform_skip_children = orig_affect_only_parents
            u.get_scene().transform_orientation_slots[0].type = orig_transform_orientation
        u.get_scene().cursor.location.xyz = orig_cursor_location
        u.get_scene().cursor.rotation_euler = orig_cursor_rotation

        self.report({'INFO'}, "Restore Rotation From Face: Done")
        return {"FINISHED"}
    

class SimpleToolbox_OT_SelectEmptyObjects(bpy.types.Operator):
    bl_label = "Check Empty Objects"
    bl_idname = "r0tools.select_empty_objects"
    bl_description = "Evaluates which objects in the scene have no or potentially unusable geometry data.\nCondition for a potentially invalid mesh is:\n    - No vertices, edges and faces\n    - No faces but has vertices (non manifold)\n\n- SHIFT: Add to current selection"
    bl_options = {'REGISTER', 'UNDO'}

    accepted_contexts = [u.OBJECT_MODES.OBJECT]

    add_to_selection: BoolProperty( # type: ignore
        name="Add to Selection",
        default=False
    )

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts

    def invoke(self, context, event):
        self.add_to_selection = False # Always reset

        if event.shift:
            self.add_to_selection = True

        return self.execute(context)
    
    def execute(self, context):
        print("\n------------- Select Empty Objects -------------")
        
        if not self.add_to_selection:
            u.deselect_all()

        flagged = []

        for obj in u.iter_scene_objects(types=[u.OBJECT_TYPES.MESH]):
            # Check if object is visible
            if not u.is_object_visible_in_viewport(obj):
                continue

            print("\nProcessing:", obj.name)

            temp_mesh = None
            temp_obj = None

            # Check for relevant modifiers that create geometry
            for modifier in obj.modifiers:
                if modifier.type in {"SOLIDIFY", "SCREW", "BOOLEAN"}:
                    # Create a temporary mesh and object
                    temp_mesh = bpy.data.meshes.new(f"{obj.name}-tempmesh-mod-check")
                    temp_obj = bpy.data.objects.new(f"{obj.name}-tempobj-mod-check", temp_mesh)
                    bpy.context.collection.objects.link(temp_obj)

                    # Copy the original object's transformations
                    temp_obj.location = obj.location.copy()
                    temp_obj.rotation_euler = obj.rotation_euler.copy()
                    temp_obj.scale = obj.scale.copy()

                    # Copy original mesh data to temporary mesh
                    temp_mesh.from_pydata(
                        [v.co for v in obj.data.vertices],
                        [list(edge.vertices) for edge in obj.data.edges],
                        [list(face.vertices) for face in obj.data.polygons]
                    )
                    temp_mesh.update()

                    # Copy relevant modifiers to the temporary object
                    for mod in obj.modifiers:
                        if mod.type in {"SOLIDIFY", "SCREW", "BOOLEAN"}:
                            new_modifier = temp_obj.modifiers.new(name=mod.name, type=mod.type)
                            for prop in dir(mod):
                                if not prop.startswith("_") and prop not in {"name", "type"}:
                                    try:
                                        setattr(new_modifier, prop, getattr(mod, prop))
                                    except AttributeError:
                                        pass  # Skip properties that don't exist

                    # Apply the modifiers
                    u.set_active_object(temp_obj)
                    for mod in temp_obj.modifiers:
                        bpy.ops.object.modifier_apply(modifier=mod.name)

                    u.deselect_object(temp_obj)
                    break  # Exit the modifiers loop

            # Create a BMesh from the temporary or original mesh
            bm = bmesh.new()
            bm.from_mesh(temp_mesh if temp_mesh else obj.data)
            bm.verts.ensure_lookup_table()

            # Check for non-manifold vertices and faces
            non_manifold_verts = [v for v in bm.verts if not v.is_manifold] if bm.verts else True # True is Manifold
            faces = [f for f in bm.faces]

            if DEBUG:
                print(f"[DEBUG] {obj.name} Vertices: {len(bm.verts)}")
                print(f"[DEBUG] {obj.name} Non-Manifold: {bool(non_manifold_verts)}")
                print(f"[DEBUG] {obj.name} Faces: {len(faces)}")

            # Flag the object if it has non-manifold vertices and no faces
            if non_manifold_verts and not faces:
                flagged.append(obj)

            # Clean up temporary objects and meshes
            if temp_obj:
                print(f"Deleting temporary object: {temp_obj.name}")
                bpy.data.objects.remove(temp_obj)
            if temp_mesh:
                print(f"Deleting temporary mesh: {temp_mesh.name}")
                bpy.data.meshes.remove(temp_mesh)

            bm.free()

        # Report the results
        msg = f"Found {len(flagged)} potentially invalid objects"
        print(msg)
        for i, flagged_obj in enumerate(flagged, start=1):
            print(f"({i}) {flagged_obj.name}")
            u.select_object(flagged_obj, set_active=(i == 1))

        self.report({'INFO'}, msg)
        
        return {'FINISHED'}
   

class SimpleToolbox_OT_ClearAxisSharpEdgesX(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_x"
    bl_description = "Clears sharp edges along the X axis"
    bl_options = {'REGISTER', 'UNDO'}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        u.op_clear_sharp_along_axis('Y') # Y so as to clear along the axis, not across it
        return {'FINISHED'}


class SimpleToolbox_OT_ClearAxisSharpEdgesY(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_y"
    bl_description = "Clears sharp edges along the Y axis"
    bl_options = {'REGISTER', 'UNDO'}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        u.op_clear_sharp_along_axis('X') # X so as to clear along the axis, not across it
        return {'FINISHED'}
    

class SimpleToolbox_OT_UVCheckIslandThresholds(bpy.types.Operator):
    bl_label = "Check UV Island Sizes"
    bl_idname = "r0tools.uv_check_island_thresholds"
    bl_description = "Iterates over UV Islands of selected objects and selects islands below defined thresholds"
    bl_options = {'REGISTER', 'UNDO'}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        print("\n------------- Check UV Islands Size Thresholds -------------")

        addon_props = u.get_addon_props()

        uv_x = addon_props.uv_target_resolution_x
        uv_y = addon_props.uv_target_resolution_y

        size_relative_threshold = addon_props.uvisland_sizecheck_arearelative if addon_props.use_uvisland_sizecheck_arearelative else 0
        size_pixel_coverage_threshold = addon_props.uvisland_sizecheck_area_pixelcoverage if addon_props.use_uvisland_sizecheck_area_pixelcoverage else 0
        size_pixel_coverage_pct_threshold = addon_props.uvisland_sizecheck_area_pixelpercentage if addon_props.use_uvisland_sizecheck_area_pixelpercentage else 0

        original_selection = bpy.context.selected_objects
        original_active = u.get_active_object()
        
        total_small_islands = 0

        if size_relative_threshold == 0:
            print(f"Not using Relative Area Size factor into account.")
        if size_pixel_coverage_threshold == 0:
            print(f"Not using Pixel Area Coverage into account.")
        if size_pixel_coverage_pct_threshold == 0:
            print(f"Not using Pixel Area Percentage factor into account.")

        u.deselect_all()

        for obj in original_selection:
            if obj.type == u.OBJECT_TYPES.MESH:
                u.select_object(obj, add=False, set_active=True)
                small_islands, small_faces, small_verts = select_small_uv_islands(
                    obj,
                    uv_x, uv_y,
                    threshold=size_relative_threshold,
                    threshold_px_coverage=size_pixel_coverage_threshold,
                    threshold_pct=size_pixel_coverage_pct_threshold
                )
                total_small_islands += len(small_islands)

        # Restore selection
        for obj in original_selection:
            u.select_object(obj)

        u.set_active_object(original_active)

        report_msg = f"Selected {total_small_islands} small island(s) across {len(original_selection)} object(s)"
        print(report_msg)
        self.report({'INFO'}, report_msg)

        return {'FINISHED'}


class SimpleToolbox_OT_ClearAxisSharpEdgesZ(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_z"
    bl_description = "Clears sharp edges along the Z axis (XY plane)"
    bl_options = {'REGISTER', 'UNDO'}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def execute(self, context):
        u.op_clear_sharp_along_axis('Z') # Z: along the XY axis
        return {'FINISHED'}


# -------------------------------------------------------------------
#   EXTERNAL OPS
# -------------------------------------------------------------------
class SimpleToolbox_OT_ApplyZenUVTD(bpy.types.Operator):
    bl_label = "Set TD"
    bl_idname = "r0tools.ext_zenuv_set_td"
    bl_description = "Apply Texel Density from ZenUV to objects"
    bl_options = {'REGISTER','UNDO'}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0
    
    def execute(self, context):
        print("\n------------- (EXT) Apply Zen UV Texel Density -------------")
        context_mode = context.mode
        
        if context_mode not in self.accepted_contexts:
            self.report({'WARNING'}, "Only performed in Object or Edit modes")
            return {'CANCELLED'}
        
        selected_objs = list(u.iter_scene_objects(selected=True))
        active_obj = bpy.context.view_layer.objects.active
        
        if context_mode == u.OBJECT_MODES.OBJECT:
            u.deselect_all()
        
        TD = u.get_td_value()
        TD_UNIT = u.get_td_unit()
        
        print(f"Setting TD {TD} for {len(selected_objs)} selected objects with {TD} px/{TD_UNIT}")
        
        u.get_scene().zen_uv.td_props.prp_current_td = TD
        u.get_scene().zen_uv.td_props.td_unit = TD_UNIT
        u.get_scene().zen_uv.td_props.td_set_mode = 'ISLAND'
        
        if context_mode == u.OBJECT_MODES.OBJECT:
        
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
                    print(f"[ERROR] Error: {e}")
                    u.context_error_debug(error=e)
                    self.report({'ERROR'}, f"Error: {e}")
                    u.deselect_object(o)
                    
            for obj in selected_objs:
                obj.select_set(True)
                
            if active_obj:
                bpy.context.view_layer.objects.active = active_obj
        elif context_mode == u.OBJECT_MODES.EDIT_MESH:
            # Add a small delay to ensure the selection is registered
            bpy.app.timers.register(lambda: None, first_interval=0.2)
            
            bpy.ops.uv.zenuv_set_texel_density(global_mode=True)
        
        # u.show_notification(f"Texel density set to {TD} px/{TD_UNIT} for {len(selected_objs)} objects.")
        self.report({'INFO'}, f"Texel density set to {TD} px/{TD_UNIT} for {len(selected_objs)} objects.")
        
        return {'FINISHED'}


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = [
    SimpleToolbox_OT_ExperimentalOP,
    
    SimpleToolbox_OT_ObjectSetsModal,
    SimpleToolbox_OT_AddObjectSetPopup,
    SimpleToolbox_OT_RenameObjectSet,
    SimpleToolbox_OT_MoveObjectSetItemUp,
    SimpleToolbox_OT_MoveObjectSetItemDown,
    SimpleToolbox_OT_RemoveObjectSet,
    SimpleToolbox_OT_AddToObjectSet,
    SimpleToolbox_OT_RemoveFromObjectSet,
    SimpleToolbox_OT_SelectObjectSet,
    
    VIEW3D_MT_CustomOrientationsPieMenu,
    SimpleToolbox_OT_ShowCustomOrientationsPie,
    TRANSFORM_OT_SetCustomOrientation,
    
    SimpleToolbox_OT_ReloadNamedScripts,
    SimpleToolbox_OT_ClearCustomSplitNormalsData,
    SimpleToolbox_OT_ClearCustomProperties,
    SimpleToolbox_OT_ClearMeshAttributes,
    SimpleToolbox_OT_ClearChildrenRecurse,
    SimpleToolbox_OT_FindModifierSearch,
    
    SimpleToolbox_OT_DissolveNthEdge,
    SimpleToolbox_OT_RestoreRotationFromSelection,
    SimpleToolbox_OT_SelectEmptyObjects,
    SimpleToolbox_OT_ClearAxisSharpEdgesX,
    SimpleToolbox_OT_ClearAxisSharpEdgesY,
    SimpleToolbox_OT_ClearAxisSharpEdgesZ,

    SimpleToolbox_OT_UVCheckIslandThresholds,

    # SimpleToolbox_OT_ApplyZenUVTD,
]

def object_sets_modal_menu_func(self, context):
    self.layout.operator(SimpleToolbox_OT_ObjectSetsModal.bl_idname)

addon_keymaps = []
def register_keymapping():
    wm = bpy.context.window_manager
    
    keymap = wm.keyconfigs.addon.keymaps.new(name="3D View", space_type="VIEW_3D")
    keymap_item = keymap.keymap_items.new(
        SimpleToolbox_OT_ShowCustomOrientationsPie.bl_idname,
        type="NONE",
        value="PRESS"
    )
    print(f"Added keymap item: {(keymap, keymap_item)}")
    addon_keymaps.append((keymap, keymap_item))

def unregister_keymapping():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    CustomTransformsOrientationsTracker.register_handler()
    
    # Register modified draw method for Orientations Pie
    _BUILTIN_ORIENTATIONS_PIE.draw = modified_orientations_pie_draw

    # Register Objects Sets Modal Operator in Viewport > View
    bpy.types.VIEW3D_MT_view.append(object_sets_modal_menu_func)
    
    # Register Objects Sets Modal Operator in Image Editor/UV > View
    bpy.types.IMAGE_MT_view.append(object_sets_modal_menu_func)
    
    register_keymapping()

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    unregister_keymapping()
    CustomTransformsOrientationsTracker.unregister_handler()

    _BUILTIN_ORIENTATIONS_PIE.draw = _ORIGINAL_ORIENTATIONS_PIE_DRAW

    # Unregister Objects Sets Modal Operator in Viewport > View
    bpy.types.VIEW3D_MT_view.remove(object_sets_modal_menu_func)

    # Unregister Objects Sets Modal Operator in Image Editor/UV > View
    bpy.types.IMAGE_MT_view.remove(object_sets_modal_menu_func)
