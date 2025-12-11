import importlib
import math
import sys
from pathlib import Path

import bmesh
import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from mathutils import Vector

from . import utils as u
from .defines import INTERNAL_NAME
from .uv_ops import select_small_uv_islands

_mod = "OPERATORS"

# ===================================================================
#   MISC
# ===================================================================

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
    # @bpy.app.handlers.persistent
    def track_custom_orientations(cls, scene, context=None):
        """
        Persistent handler to monitor and track changes in custom transform orientations.

        :param scene: Current Blender scene
        :param context: Optional context
        """

        if u.is_debug():
            print(f"------------- Track Custom Orientations -------------")

        if not u.is_writing_context_safe(scene):
            return None

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
                    if u.is_debug():
                        print(f"[INFO] [{_mod}] Custom Orientation Added: {orient}")

                for orient in removed_orientations:
                    if u.is_debug():
                        print(f"[DEBUG] [{_mod}] Custom Orientation Removed: {orient}")

                # Update the last tracked set
                cls._last_tracked_orientations = current_orientation_set

                # Update UI
                # for area in bpy.context.screen.areas:
                # area.tag_redraw()
        except Exception as e:
            u.log(f"[ERROR] [{_mod}] Error tracking custom orientations: {e}")
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
        # cls.unregister_handler()

        # >>>>> Moved to depsgraph.py and handled there
        # u.LOG(f"[INFO] [{_mod}] Register depsgraph_handler_post: {cls.track_custom_orientations.__name__}")
        # bpy.app.handlers.depsgraph_update_post.append(cls.track_custom_orientations)
        # <<<<<

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
            u.log(f"[INFO] [{_mod}] Unregister depsgraph_handler_post: {cls.track_custom_orientations.__name__}")
            bpy.app.handlers.depsgraph_update_post.remove(cls.track_custom_orientations)


class TRANSFORM_OT_SetCustomOrientation(bpy.types.Operator):
    """
    Operator responsible for picking the chosen Custom Transform Orientations from the Custom Transform Orientations Menu
    """

    bl_label = "Set Custom Orientation"
    bl_idname = "r0tools.set_custom_orientation"
    bl_description = "Sets the picked Custom Transform Orientation"

    orientation: StringProperty(name="Orientation")  # type: ignore

    def execute(self, context):
        # Reset the _invoked flag after selecting an orientation
        VIEW3D_MT_CustomOrientationsPieMenu._invoked = True

        try:
            if self.orientation in u.get_custom_transform_orientations():
                u.get_scene().transform_orientation_slots[0].type = self.orientation
            else:
                CustomTransformsOrientationsTracker.track_custom_orientations(bpy.context.scene)
                report_msg = f"Custom Transform Orientation '{self.orientation}' not found."
                self.report({"WARNING"}, report_msg)
                u.log(f"[WARNING] [{_mod}] {report_msg}")
            return {"FINISHED"}
        except Exception as err:
            report_msg = f"Could not set orientation: {err}"
            self.report({"ERROR"}, report_msg)
            print(f"[ERROR] [{_mod}] Could not set orientation: {err}")
            u.context_error_debug(error=err)
            return {"CANCELLED"}


class BUILTINS_OT_IconViewer(bpy.types.Operator):
    bl_label = "Icon Viewer"
    bl_idname = "r0tools.icon_viewer"
    bl_description = "Show the built-in Icon Viewer"
    bl_options = {"REGISTER"}

    def execute(self, context):
        addon_name = "bl_ext.blender_org.icon_viewer"
        if addon_name not in bpy.context.preferences.addons:
            # bpy.ops.preferences.addon_enable(module=addon_name)
            return {"FINISHED"}

        bpy.ops.iv.icons_show("INVOKE_DEFAULT")

        return {"FINISHED"}


# ===================================================================
#   PIE MENUS
# ===================================================================
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
            u.log(
                f"[INFO] [{_mod}] Not drawing Custom Transform Orientations Pie: '{u.get_context_area()} not in valid context areas: {cls._VALID_CONTEXTS}"
            )
            return False
        return True

    @classmethod
    def reset(cls):
        """Reset relevant class flags"""
        cls._current_start_index = 0
        cls._invoked = True

    def draw(self, context):
        u.log(f"[INFO] [{_mod}] Draw Custom Transform Orientations Pie Menu")
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

        if u.is_debug():
            print(f"[DEBUG] [{_mod}] {remaining_orientations=}")
            print(f"[DEBUG] [{_mod}] {start_index=}")
            print(f"[DEBUG] [{_mod}] {end_index=}")

        total_added = 0  # 8 is the maximum allowed
        for orientation_name in custom_orientations[self.__class__._current_start_index :]:
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
                if u.is_debug():
                    print(f"[DEBUG] [{_mod}] ({self.__class__._current_start_index}) {orientation_name}")
            except Exception as err:
                print(f"[ERROR] [{_mod}] Error adding Custom Orientation to Pie Menu: {err}")
                u.context_error_debug(error=err)

            # "View More" if there are additional orientations
            if total_added == 7 and remaining_orientations > 8:
                try:
                    op = pie.operator("wm.call_menu_pie", text="View More", text_ctxt="Orientation")
                    op.name = "VIEW3D_MT_r0_custom_orientations_pie"

                    # Store the next starting index for the next call
                    # Compensate for now showing last entry with -1, so index starts at missing entry from this round
                    self.__class__._current_start_index = end_index - 1
                    # Ensure we're not treating it as invoked
                    self.__class__._invoked = False

                    # Update iterations
                    total_added += 1
                    if u.is_debug():
                        print(f"[DEBUG] [{_mod}] ({self.__class__._current_start_index}) {orientation_name}")
                except Exception as err:
                    print(f"[ERROR] [{_mod}] Error adding View More to Pie Menu: {err}")
                    u.context_error_debug(error=err)

            # Break the fill loop if we've successfully filled 8 entries
            if total_added >= 8:
                if u.is_debug():
                    print(f"[DEBUG] [{_mod}] Menu entries limit reached! Total added: {total_added}")
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
        return {"FINISHED"}


# ===================================================================
#   EXPERIMENTAL
# ===================================================================
class SimpleToolbox_OT_ExperimentalOP(bpy.types.Operator):
    bl_label = "Exp Op 1"
    bl_idname = "r0tools.experimental_op_1"
    bl_description = ""
    bl_options = {"REGISTER"}

    def get_viewport(self, context):
        # Get the active 3D viewport
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                # Get the region and region 3D view
                region = None
                rv3d = None
                for r in area.regions:
                    if r.type == "WINDOW":
                        region = r
                        break
                rv3d = area.spaces[0].region_3d

                # Exit the loop once we find a valid viewport
                break

        # Validate viewport
        if not (region and rv3d):
            self.report({"ERROR"}, "Could not find 3D viewport")
            return (None, None)

        return region, rv3d

    def get_loose_vertices(self, obj):
        obj_verts = [v.index for v in obj.data.vertices]
        loop_verts = []  # Vertices which are part of a loop
        loose_verts = []

        # bpy.ops.mesh.select_non_manifold() # Requires Edit Mode

        for p in obj.data.polygons:
            poly_idx = p.index
            poly_verts = [p.vertices[0], p.vertices[1], p.vertices[2]]
            loop_verts.append(poly_verts)

            if u.is_debug():
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
            if u.is_debug():
                print(f"[DEBUG] [{_mod}] {obj.name} has {len(loose_verts)} loose vertices: {loose_verts}")

        return loose_verts

    def execute(self, context):
        u.log("\n------------- Experimental Operator 1 -------------")
        region, rv3d = self.get_viewport(context)

        # Get the actual viewport dimensions
        viewport_width = region.width
        viewport_height = region.height
        viewport_diagonal = math.sqrt(viewport_width**2 + viewport_height**2)

        u.log(f"[INFO] [{_mod}] Viewport WxH: {viewport_width}x{viewport_height}")

        orig_active = context.view_layer.objects.active

        visible_objects = [o for o in u.iter_scene_objects() if o.visible_get()]

        for o in visible_objects:
            self.get_loose_vertices(o)

        context.view_layer.objects.active = orig_active

        return {"FINISHED"}


# ===================================================================
#   DEV OPS
# ===================================================================
class SimpleToolbox_OT_ReloadNamedScripts(bpy.types.Operator):
    bl_label = "Reload Script(s)"
    bl_idname = "r0tools.reload_named_scripts"
    bl_description = "Reload only specified scripts from a name text box"
    bl_options = {"REGISTER"}

    def get_input_modules(self) -> list[str]:
        text = u.get_addon_props().reload_modules_prop
        modules = []
        if text:
            modules.extend([t.strip() for t in text.split(",")])

        return modules

    def reload_module(self, mod_name) -> bool:
        try:
            # Check if the module is already imported
            if mod_name in sys.modules:
                # Reload the module
                module = sys.modules[mod_name]
                importlib.reload(module)

                # If it's an addon, re-register its classes
                if hasattr(module, "register"):
                    try:
                        module.unregister()
                    except Exception as unreg_err:
                        print(f"[ERROR] [{_mod}] Error unregistering {mod_name}: {unreg_err}")

                    try:
                        module.register()
                    except Exception as reg_err:
                        print(f"[ERROR] [{_mod}] Error re-registering {mod_name}: {reg_err}")

                u.log(f"[INFO] [{_mod}] Reloaded {mod_name}")
                return True
            else:
                u.log(f"[INFO] [{_mod}] Module {mod_name} not found in sys.modules")
                return False
        except Exception as e:
            print(f"[ERROR] [{_mod}] Error reloading {mod_name}: {e}")
            return False

    def execute(self, context):
        u.log("\n------------- Reload Named Scripts -------------")
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
                    u.log(e)
                    success = False
                if success:
                    successes.append(module)
                else:
                    failures.append(module)

        u.log(f"[INFO] [{_mod}] Reloaded: {successes}")
        u.log(f"[INFO] [{_mod}] Failed: {failures}")

        reload_msg = f"Reloaded {len(successes)}. Unable to reload {len(failures)}"

        try:
            self.report({"INFO"}, reload_msg)
        except Exception as e:
            print(f"[ERROR] [{_mod}] Error reporting results: {e}")

        u.show_notification(reload_msg)

        return {"FINISHED"}


class SimpleToolbox_OT_FixImageDataPaths(bpy.types.Operator):
    bl_label = "Fix Image Data Paths"
    bl_idname = "r0tools.fix_image_data_paths"
    bl_description = "Attempts to fix image data paths for broken link/filepath data references.\n-SHIFT: Dry Run (will not make any changes. Check terminal for output)"
    bl_options = {"REGISTER", "UNDO"}

    dry_run: BoolProperty(default=False, name="Dry Run")  # type: ignore

    def invoke(self, context, event):
        self.dry_run = False  # Always reset

        if event.shift:
            self.dry_run = True

        return self.execute(context)

    def execute(self, context):
        blender_version = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
        config_path = u.get_bl_config_path()

        if not config_path:
            u.log(f"[WARNING] [{_mod}] Config path '{config_path}' is not valid.")
            return {"FINISHED"}

        for image in bpy.data.images:
            fp: str = image.filepath

            is_relative_fp: bool = fp.startswith("//") or fp.startswith("\\\\")

            if not Path(fp).exists() and not is_relative_fp:
                fp_split = fp.split(blender_version)
                if len(fp_split) > 1:
                    u.log(f"[INFO] [{_mod}] Fix  : {fp}")
                    fp_fix = config_path + fp_split[1]
                    if Path(fp_fix).exists():
                        if not self.dry_run:
                            image.filepath = fp_fix
                            u.log(f"[INFO] [{_mod}] Fixed: {fp_fix}")
                        else:
                            u.log(f"[INFO] [{_mod}] [DRY] Fixed: {fp_fix}")
                    else:
                        u.log(f"[INFO] [{_mod}] Not fixed: {fp} -> ({fp_fix})")
                    u.log()

        return {"FINISHED"}


# ===================================================================
#   OBJECT OPS
# ===================================================================
class SimpleToolbox_OT_ClearChildrenRecurse(bpy.types.Operator):
    bl_label = "Clear Children"
    bl_idname = "r0tools.clear_all_objects_children"
    bl_description = "For each selected object, clears parenting keeping transform for each child object.\n\n- SHIFT: Recursively clears parenting for ALL object children and sub-children"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return u.get_selected_objects(context) and context.mode == u.OBJECT_MODES.OBJECT

    recurse: BoolProperty(name="Recursively clear all children", default=False)  # type: ignore

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
        bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")

        if was_hidden:
            child.hide_set(True)

        if was_hidden_viewport:
            child.hide_viewport = True

    def invoke(self, context, event):
        self.recurse = False  # Always reset

        if event.shift:
            self.recurse = True

        return self.execute(context)

    def execute(self, context):
        if u.is_debug():
            print("\n------------- Clear Object(s) Children -------------")
        parent_objs = 0
        total_children_cleared = 0

        problem_objects = []

        active_obj = bpy.context.view_layer.objects.active

        # Match selected objects' data names to mesh names
        for o in u.iter_scene_objects(selected=True):
            if u.is_debug():
                print(f"[DEBUG] [{_mod}] Iter {o.name}")

            for child in u.iter_obj_children(o, recursive=self.recurse):
                # u.LOG(f"[INFO] [{_mod}] Child: {child.name}")
                try:
                    self.process_child_object(child)
                    total_children_cleared += 1
                except Exception as e:
                    print(f"[ERROR] [{_mod}]: {e}")
                    u.context_error_debug(error=e)
                    problem_objects.append(child)

            parent_objs += 1

        bpy.context.view_layer.objects.active = active_obj

        cleared_msg = f"Cleared {total_children_cleared} child objects for {parent_objs} main objects."
        # u.show_notification(cleared_msg)
        self.report({"INFO"}, cleared_msg)

        if problem_objects:
            u.deselect_all()
            for obj in problem_objects:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
                    child.hide_set(False)
                    child.hide_viewport = False
            issues_msg = f"The following objects have raised issues: {', '.join([obj.name for obj in problem_objects])}"
            u.show_notification(issues_msg)
            self.report({"WARNING"}, issues_msg)

        return {"FINISHED"}


class SimpleToolbox_OT_RemoveUnusedMaterials(bpy.types.Operator):
    bl_idname = "r0tools.remove_unused_material_slots"
    bl_label = "Remove Unused Materials"
    bl_description = "Runs the operator to remove all unused materials across all selected objects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT and u.get_selected_objects(context)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        if u.is_debug():
            print("\n------------- Remove Unused Materials -------------")

        original_active = u.get_active_object()

        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            # Set active object
            u.set_active_object(obj)

            if u.is_debug():
                print(f"[DEBUG] [{_mod}] Processing '{obj.name}'")

            bpy.ops.object.material_slot_remove_unused()

        u.set_active_object(original_active)

        return {"FINISHED"}


class SimpleToolbox_OT_FindModifierSearch(bpy.types.Operator):
    bl_idname = "r0tools.find_modifier_search"
    bl_label = "Find Modifiers"
    bl_description = 'Find and select objects whose modifier name(s) or type(s) match the given search text criteria.\nTo search for a mix of name and type and/or multiple criteria, use a comma-separated string, ex.: "!!, weld, nodes"\nNote: Case Insensitive\n\n- SHIFT: Add to selection'
    bl_options = {"INTERNAL"}

    add_to_selection: BoolProperty(default=False, name="Add To Selection")  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT

    def invoke(self, context, event):
        self.add_to_selection = False  # Always reset

        if event.shift:
            self.add_to_selection = True

        return self.execute(context)

    def execute(self, context):
        addon_props = u.get_addon_props()
        addon_find_modifier_props = u.get_addon_find_modifier_props()

        if u.is_debug():
            print("\n------------- Find Modifier(s) Search -------------")

        search_text = addon_props.find_modifier_search_text.lower()
        search_terms = [s.strip() for s in search_text.split(",") if s.strip()]

        if u.is_debug():
            print(f"[DEBUG] [{_mod}] {search_text=}")
            print(f"[DEBUG] [{_mod}] (FLAG) {self.add_to_selection=}")

        # Use a dictionary to group objects by category.
        # The key will be the modifier name, example: "DATA_TRANSFER".
        # Value is a Set to handle duplicates automatically.
        found_by_category = {}
        mod_names_and_types = {}

        if search_terms:
            view_layer_objs = bpy.context.view_layer.objects

            for obj in view_layer_objs:
                if not u.object_visible(obj):
                    continue

                obj_modifiers = obj.modifiers
                for modifier in obj_modifiers:
                    mod_name = modifier.name.lower()
                    mod_type_lower = modifier.type.lower()

                    mod_type_key = modifier.name

                    for term in search_terms:
                        if term in mod_name or term in mod_type_lower:
                            if u.is_debug():
                                print(
                                    f"[DEBUG] [{_mod}] Match: '{term}' in '{mod_name}' or '{mod_type_lower}' on object '{obj.name}'"
                                )

                            if mod_type_key not in found_by_category:
                                found_by_category[mod_type_key] = set()

                            found_by_category[mod_type_key].add(obj)
                            mod_names_and_types[modifier.name] = modifier.type

        if u.is_writing_context_safe(context.scene):
            found_objects_collection = addon_find_modifier_props.objects_list.found_objects
            found_objects_collection.clear()

            # Sort categories alphabetically
            sorted_categories = sorted(found_by_category.keys())

            for category in sorted_categories:
                header_item = found_objects_collection.add()

                # header_item.category_name = category.replace("_", " ").title()
                cat_mod_type = mod_names_and_types.get(category)
                header_item.category_name = f"{category} ({cat_mod_type})"

                # Sort objects alphabetically
                objects_in_category = sorted(list(found_by_category[category]), key=lambda o: o.name)
                for obj in objects_in_category:
                    list_item = found_objects_collection.add()
                    list_item.obj = obj

        all_unique_objects = set()
        if found_by_category:
            # The * operator unpacks the sets from the dictionary values
            all_unique_objects = set().union(*found_by_category.values())

        sorted_objects = sorted(list(all_unique_objects), key=lambda o: o.name)

        if not self.add_to_selection:
            u.deselect_all()

        if sorted_objects:
            for obj in sorted_objects:
                u.select_object(obj, add=True)

            u.set_active_object(sorted_objects[-1])

        if not found_by_category and search_terms:
            self.report({"INFO"}, "No objects found with matching modifiers.")

        return {"FINISHED"}


class SimpleToolbox_OT_FindModifierSelectObject(bpy.types.Operator):
    bl_idname = "r0tools.find_modifier_select_object"
    bl_label = "Select Object"
    bl_description = "Select this object and make it active.\n\n- SHIFT: Add to selection"
    bl_options = {"REGISTER", "UNDO"}

    # This property will receive the object name from the UIList button.
    object_name: bpy.props.StringProperty(default="")  # type: ignore
    add_to_selection: bpy.props.BoolProperty(default=False)  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT

    def invoke(self, context, event):
        self.add_to_selection = False  # Always reset

        if event.shift:
            self.add_to_selection = True

        return self.execute(context)

    def execute(self, context):
        """
        if self.select_all:
            return self.execute_select_all(context)
        else:
            return self.execute_select_single(context)
        """

        return self.execute_select_single(context)

    def execute_select_all(self, context):
        """Unused"""
        addon_find_modifier_props = u.get_addon_find_modifier_props()
        found_items = addon_find_modifier_props.objects_list.found_objects

        if not found_items:
            self.report({"WARNING"}, "No objects in the list to select.")
            return {"CANCELLED"}

        if not self.add_to_selection:
            u.deselect_all()

        objects_to_select = []
        for item in found_items:
            if item.obj:
                objects_to_select.append(item.obj)

        if not objects_to_select:
            return {"CANCELLED"}

        for obj in objects_to_select:
            obj.select_set(True)

        context.view_layer.objects.active = objects_to_select[0]

        return {"FINISHED"}

    def execute_select_single(self, context):
        if not self.object_name:
            self.report({"WARNING"}, "No object name provided.")
            return {"CANCELLED"}

        target_obj = bpy.data.objects.get(self.object_name)
        if not target_obj:
            self.report({"WARNING"}, f"Object '{self.object_name}' not found.")
            return {"CANCELLED"}

        if self.add_to_selection:
            u.select_object(target_obj, add=True, set_active=True)
        else:
            u.deselect_all()
            u.select_object(target_obj, add=False, set_active=True)

        return {"FINISHED"}


class SimpleToolbox_OT_FindModifierSelectCategory(bpy.types.Operator):
    bl_idname = "r0tools.find_modifier_select_category"
    bl_label = "Select in Category"
    bl_description = "Selects all objects in a Category"
    bl_options = {"REGISTER", "UNDO"}

    category_name: StringProperty()  # type: ignore

    extend: BoolProperty(
        name="Extend Selection", description="Add to existing selection", default=False
    )  # type: ignore

    def invoke(self, context, event):
        self.extend = event.shift
        return self.execute(context)

    def execute(self, context):
        find_modifier_props = u.get_addon_find_modifier_props()
        found_objects_collection = find_modifier_props.objects_list.found_objects

        if not self.extend:
            u.deselect_all()

        objects_to_select = []
        in_target_category = False

        for item in found_objects_collection:
            if item.category_name:
                # Found category header
                if item.category_name == self.category_name:
                    in_target_category = True
                elif in_target_category:
                    # Stop when detected another target category
                    break
            elif in_target_category and item.obj:
                objects_to_select.append(item.obj)

        if not objects_to_select:
            self.report({"WARNING"}, f"No objects found in category '{self.category_name}'")

        for obj in objects_to_select:
            u.select_object(obj, add=True, set_active=True)

        return {"FINISHED"}


class SimpleToolbox_OT_FindModifierClearList(bpy.types.Operator):
    bl_idname = "r0tools.find_modifier_clear_list"
    bl_label = "Clear List"
    bl_description = "Clears the found objects list"
    bl_options = {"REGISTER"}

    def execute(self, context):
        if u.is_writing_context_safe(context.scene):
            addon_find_modifier_props = u.get_addon_find_modifier_props()
            addon_find_modifier_props.objects_list.found_objects.clear()

        return {"FINISHED"}


class SimpleToolbox_OT_ToggleWireDisplay(bpy.types.Operator):
    """Toggle Wire Display"""

    bl_idname = "r0tools.toggle_wire_display_mode"
    bl_label = "Toggle Wire Display"

    def execute(self, context):
        wires = 0
        textureds = 0
        other = 0
        objects = [obj for obj in u.get_selected_objects() if obj and obj.type == "MESH"]

        if not objects:
            return {"FINISHED"}

        for obj in objects:
            if obj.display_type == "WIRE":
                wires += 1
            elif obj.display_type == "TEXTURED":
                textureds += 1
            else:
                other += 1  # SOLID, BOUNDING_BOX, or other modes

        display_mode = "TEXTURED"  # Default
        vp_show_wire = False  # Default

        if wires > textureds and textureds > 0:
            if u.is_debug():
                print(f"[INFO] [{_mod}] 1")
            display_mode = "WIRE"
            vp_show_wire = True
        elif textureds > wires and wires > 0:
            if u.is_debug():
                print(f"[INFO] [{_mod}] 2")
            display_mode = "TEXTURED"
            vp_show_wire = False
        elif other == len(objects):  # If all objects are neither wire nor textured
            if u.is_debug():
                print(f"[INFO] [{_mod}] 3")
            display_mode = "WIRE"
            vp_show_wire = True
        else:
            # Default case
            display_mode = "WIRE" if wires == 0 else "TEXTURED"
            vp_show_wire = True if wires == 0 else False

        # Apply the new display type
        for obj in objects:
            obj.display_type = display_mode
            obj.show_wire = vp_show_wire  # Helps revert Hops alteration

        return {"FINISHED"}


# ===================================================================
#   MESH OPS
# ===================================================================
class SimpleToolbox_OT_DissolveNthEdge(bpy.types.Operator):
    bl_label = "Remove Nth Edges"
    bl_idname = "r0tools.nth_edges_dissolve"
    bl_description = "Remove Nth (every other) edges from edge loops.\nSelect one edge per disconnected mesh to define the starting point.\n\nBy default, the selection automatically expands to include all connected edges in the loop. To limit the operation to only the manually selected contiguous edges or restrict it to the original ring selection, disable 'Expand Edges.'"
    bl_options = {"REGISTER", "UNDO"}

    expand_edges: BoolProperty(name="Expand Edges", default=True)  # type: ignore
    keep_initial_selection: BoolProperty(name="Keep Selected Edges", default=True)  # type: ignore

    @classmethod
    def poll(cls, context):
        # Ensure at least one object is selected
        return u.get_selected_objects(context) and context.mode == u.OBJECT_MODES.EDIT_MESH

    def process_object(self, obj, context):
        if u.is_debug():
            print(f"[DEBUG] [{_mod}] Processing {obj.name}")

        # Ensure Object Mode
        if context.mode != u.OBJECT_MODES.OBJECT:
            u.set_mode_object()

        # Deselect all, and only select relevant object to operate on
        u.deselect_all()

        # Make active
        u.select_object(obj, add=False, set_active=True)

        if context.mode != u.OBJECT_MODES.EDIT_MESH:
            u.set_mode_edit()

        # Create a bmesh
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.edges.ensure_lookup_table()
        bm.select_mode = {"EDGE"}

        # Currently selected edges from all meshes
        # Ideally this should only be 1 edge per disconnected mesh
        initial_selection = [edge for edge in bm.edges if edge.select]

        # Edges to delete from all meshes
        edges_delete = []

        for i, edge in enumerate(initial_selection):
            if u.is_debug():
                print(f"[DEBUG] [{_mod}] {i} {edge.index}")

            # Deselect all bm edges
            for e in bm.edges:
                e.select = False

            # Select the one edge being iterated
            edge.select = True
            bm.select_history.clear()  # Optionally clear previous elements
            bm.select_history.add(edge)  # Make active edge

            # Select the ring and nth
            bpy.ops.mesh.loop_multi_select(ring=True)

            total_selected = len([edge for edge in bm.edges if edge.select])
            if u.is_debug():
                print(f"[DEBUG] [{_mod}] Total Before Nth: {total_selected}")

            bpy.ops.mesh.select_nth()

            selected_edges = [edge.index for edge in bm.edges if edge.select]

            remaining_edges = total_selected - len(selected_edges)
            if u.is_debug():
                print(f"[DEBUG] [{_mod}] Estimated remaining edges: {remaining_edges}")

            if remaining_edges < 3:
                # We've hit below the threshold, don't process this object
                for e in bm.edges:
                    e.select = False
                continue

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
        bm.select_history.validate()  # Ensure that only selected elements are in select_history

        bpy.ops.mesh.dissolve_mode(use_verts=True)

        # Update the mesh
        bmesh.update_edit_mesh(me)
        bm.free()

        # Select initial selection of edges
        if self.keep_initial_selection:
            for edge in initial_selection:
                if edge.is_valid:
                    edge.select = True

        u.set_mode_object()

    def execute(self, context):
        if u.is_debug():
            print("\n------------- Dissolve Nth Edges -------------")

        original_active_obj = context.active_object
        original_mode = context.mode

        if original_mode != u.OBJECT_MODES.OBJECT:
            u.set_mode_object()

        # Collect selected mesh objects
        selected_objects = [obj for obj in context.selected_objects if obj.type == u.OBJECT_TYPES.MESH]
        for obj in selected_objects:
            self.process_object(obj, context)

        # Restore selection
        for obj in selected_objects:
            u.select_object(obj, add=True)
        u.set_active_object(original_active_obj)

        # Return to the original active object and mode
        u.set_object_mode(original_mode)

        return {"FINISHED"}


class SimpleToolbox_OT_RestoreNthEdge(bpy.types.Operator):
    bl_label = "Restore Nth Edges"
    bl_idname = "r0tools.nth_edges_restore"
    bl_description = "Restore Nth (every other) edges from edge loops.\nSelect one edge per disconnected mesh to define the starting point.\n\nBy default, the selection automatically expands to include all connected edges in the loop. To limit the operation to only the manually selected contiguous edges or restrict it to the original ring selection, disable 'Expand Edges.'"
    bl_options = {"REGISTER", "UNDO"}

    expand_edges: BoolProperty(name="Expand Edges", default=True)  # type: ignore
    keep_initial_selection: BoolProperty(name="Keep Selected Edges", default=True)  # type: ignore

    @classmethod
    def poll(cls, context):
        # Ensure at least one object is selected
        return u.get_selected_objects(context) and context.mode == u.OBJECT_MODES.EDIT_MESH

    def process_object(self, obj, context):
        if u.is_debug():
            print(f"[DEBUG] [{_mod}] Processing {obj.name}")

        # Ensure Object Mode
        if context.mode != u.OBJECT_MODES.OBJECT:
            u.set_mode_object()

        # Deselect all, and only select relevant object to operate on
        u.deselect_all()

        # Make active
        u.select_object(obj, add=False, set_active=True)

        if context.mode != u.OBJECT_MODES.EDIT_MESH:
            u.set_mode_edit()

        # Create a bmesh
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.edges.ensure_lookup_table()
        bm.select_mode = {"EDGE"}

        # Currently selected edges from all meshes
        # Ideally this should only be 1 edge per disconnected mesh
        initial_selection = [edge for edge in bm.edges if edge.select]

        for i, edge in enumerate(initial_selection):
            if u.is_debug():
                print(f"[DEBUG] [{_mod}] {i} {edge.index}")

            # Deselect all bm edges
            for e in bm.edges:
                e.select = False

            # Select the one edge being iterated
            edge.select = True
            bm.select_history.clear()  # Optionally clear previous elements
            bm.select_history.add(edge)  # Make active edge

            # Select the coplanar edge ring
            bpy.ops.mesh.loop_multi_select(ring=False)
            # Propagate the selection "upward"
            bpy.ops.mesh.loop_multi_select(ring=True)

            bpy.ops.mesh.subdivide()

        # Make sure to deselect all bm edges too
        for e in bm.edges:
            e.select = False

        for edge in initial_selection:
            edge.select = True
        bm.select_history.validate()  # Ensure that only selected elements are in select_history

        # Loop around and "up" and circularise
        bpy.ops.mesh.loop_multi_select(ring=False)
        bpy.ops.mesh.loop_multi_select(ring=True)
        bpy.ops.mesh.looptools_circle(
            custom_radius=False,
            fit="best",
            flatten=True,
            influence=100,
            lock_x=False,
            lock_y=False,
            lock_z=False,
            radius=1,
            angle=0,
            regular=True,
        )

        # Select initial selection of edges
        for e in bm.edges:
            e.select = False

        if self.keep_initial_selection:
            u.log(f"[INFO] [{_mod}] {initial_selection}")
            for edge in initial_selection:
                edge.select = True

        # Update the mesh
        bmesh.update_edit_mesh(me)
        bm.free()

        u.set_mode_object()

    def execute(self, context):
        if u.is_debug():
            print("\n------------- Restore Nth Edges -------------")

        original_active_obj = context.active_object
        original_mode = context.mode

        if original_mode != u.OBJECT_MODES.OBJECT:
            u.set_mode_object()

        # Collect selected mesh objects
        selected_objects = [obj for obj in context.selected_objects if obj.type == u.OBJECT_TYPES.MESH]
        for obj in selected_objects:
            self.process_object(obj, context)

        # Ensure object mode for selection restoraion
        if original_mode != u.OBJECT_MODES.OBJECT:
            u.set_mode_object()

        # Restore selection
        for obj in selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = original_active_obj

        # Return to the original active object and mode
        u.set_object_mode(original_mode)

        return {"FINISHED"}


class SimpleToolbox_OT_ResetEdgeData(bpy.types.Operator):
    bl_label = "Reset Edge Data"
    bl_idname = "r0tools.reset_edge_data"
    bl_description = "Removes Seams, Sharps, Creases and Bevel Edge Weights from edges"
    bl_options = {"REGISTER", "UNDO"}

    reset_sharp: BoolProperty(name="Sharp", default=True)  # type: ignore
    reset_seam: BoolProperty(name="Seam", default=True)  # type: ignore
    reset_crease: BoolProperty(name="Crease", default=True)  # type: ignore
    reset_bevel_weight: BoolProperty(name="Bevel Weight", default=True)  # type: ignore

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Pick what to affect. Changes are persistent.", icon="INFO")

        row = layout.row()
        split = row.split(align=True)
        split.prop(self, "reset_sharp")
        split.prop(self, "reset_seam")

        row = layout.row()
        split = row.split(align=True)
        split.prop(self, "reset_crease")
        split.prop(self, "reset_bevel_weight")

    @classmethod
    def poll(cls, context):
        return u.get_selected_objects(context) and context.mode == u.OBJECT_MODES.EDIT_MESH

    def invoke(self, context, event):
        addon_prefs = u.get_addon_prefs()

        self.reset_sharp = addon_prefs.edge_reset_sharp
        self.reset_seam = addon_prefs.edge_reset_seam
        self.reset_crease = addon_prefs.edge_reset_crease
        self.reset_bevel_weight = addon_prefs.edge_reset_bevel_weight

        # Show the redo panel
        # return context.window_manager.invoke_props_dialog(self)

        return self.execute(context)

    def execute(self, context):
        addon_prefs = u.get_addon_prefs()

        # Sync operator preferences to Addon Preferences
        addon_prefs.edge_reset_sharp = self.reset_sharp
        addon_prefs.edge_reset_seam = self.reset_seam
        addon_prefs.edge_reset_crease = self.reset_crease
        addon_prefs.edge_reset_bevel_weight = self.reset_bevel_weight

        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            bm = bmesh.from_edit_mesh(obj.data)

            bm.edges.ensure_lookup_table()

            crease_layer = u.bmesh_get_crease_layer(bm)
            edge_bevel_layer = u.bmesh_get_bevel_weight_edge_layer(bm)

            for edge in bm.edges:
                if edge.select:
                    if self.reset_seam:
                        edge.seam = False
                    if self.reset_sharp:
                        edge.smooth = True  # smooth=True means sharp=False
                    if self.reset_crease and crease_layer:
                        edge[crease_layer] = 0.0

                    if self.reset_bevel_weight and edge_bevel_layer:
                        edge[edge_bevel_layer] = 0.0

            bmesh.update_edit_mesh(obj.data)

        return {"FINISHED"}


class SimpleToolbox_OT_RestoreRotationFromSelection(bpy.types.Operator):
    bl_label = "Restore Rotation"
    bl_idname = "r0tools.rotation_from_selection"
    bl_description = "Given a selection of vertices/edges/faces, align each object such that the selection aligns to the Z Axis.\n\n- SHIFT: Clear object rotations on finish. (Also present in Redo panel)"
    bl_options = {"REGISTER", "UNDO"}

    clear_rotation_on_align: BoolProperty(name="Clear Rotation(s)", default=False)  # type: ignore
    origin_to_selection: BoolProperty(name="Origin to selection", default=False)  # type: ignore
    keep_original_tool_configs: BoolProperty(name="Restore Tool Configurations", default=True)  # type: ignore

    @classmethod
    def poll(cls, context):
        return u.get_selected_objects(context) and context.mode == u.OBJECT_MODES.EDIT_MESH

    def invoke(self, context, event):
        self.clear_rotation_on_align = False  # Always reset
        self.origin_to_selection = False  # Always reset

        if event.shift:
            self.clear_rotation_on_align = True

        return self.execute(context)

    def execute(self, context):
        u.log("\n------------- Restore Rotation From Selection -------------")
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
            if u.is_debug():
                print(f"[DEBUG] [{_mod}] Iterating Object: {obj.name}")
            u.select_object(obj, add=False, set_active=True)
            u.set_mode_edit()

            # TODO: Check for selected loops/polygons, otherwise, skip.

            # Create Transform Orientation
            to_name = f"{obj.name}_restore_orientation"
            transform_orientation_names.append(to_name)
            bpy.ops.transform.create_orientation(name=to_name, use=True)  # Immediately set to use it

            u.set_mode_object()

            # Affect only origins
            u.get_scene().tool_settings.use_transform_data_origin = True
            u.get_scene().tool_settings.use_transform_pivot_point_align = False
            u.get_scene().tool_settings.use_transform_skip_children = False

            # Align to Transform Orientation
            bpy.ops.transform.transform(mode="ALIGN")

            # Clear affect only origins
            u.get_scene().tool_settings.use_transform_data_origin = False

            # Conditionally clear rotations based on property
            if self.clear_rotation_on_align:
                if u.is_debug():
                    print(f"[DEBUG] [{_mod}] Clearing Rotation for {obj.name}")
                obj.rotation_euler = (0, 0, 0)
            else:
                if u.is_debug():
                    print(f"[DEBUG] [{_mod}] Keeping Rotation for {obj.name}")

            # Check if we're just setting origin to transform
            if self.origin_to_selection:
                u.set_mode_edit()
                if u.is_debug():
                    print(f"[DEBUG] [{_mod}] Setting object origin to median of selection for {obj.name}")
                bpy.ops.view3d.snap_cursor_to_selected()
                u.set_mode_object()
                bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")

        # Restore selection
        for obj in orig_selected_objects:
            u.select_object(obj)  # Add to selection
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

        self.report({"INFO"}, "Restore Rotation From Face: Done")
        return {"FINISHED"}


class SimpleToolbox_OT_SelectEmptyObjects(bpy.types.Operator):
    bl_label = "Check Empty Objects"
    bl_idname = "r0tools.select_empty_objects"
    bl_description = "Evaluates which objects in the scene have no or potentially unusable geometry data.\nCondition for a potentially invalid mesh is:\n    - No vertices, edges and faces\n    - No faces but has vertices (non manifold)\nCondition for a potentially invalid curve is:\n    - Less that 1 or no spline points\n\n- SHIFT: Add to current selection"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT]

    add_to_selection: BoolProperty(name="Add to Selection", default=False)  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts

    def invoke(self, context, event):
        self.add_to_selection = False  # Always reset

        if event.shift:
            self.add_to_selection = True

        return self.execute(context)

    def execute(self, context):
        u.log("\n------------- Select Empty Objects -------------")

        if not self.add_to_selection:
            u.deselect_all()

        flagged = []

        # Process mesh objects
        for obj in u.iter_scene_objects(types=[u.OBJECT_TYPES.MESH]):
            # Check if object is visible
            if not u.is_object_visible_in_viewport(obj):
                continue

            u.log(f"[INFO] [{_mod}] Processing: {obj.name}")

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
                        [list(face.vertices) for face in obj.data.polygons],
                    )
                    temp_mesh.update()

                    # Copy relevant modifiers to the temporary object
                    for mod in obj.modifiers:
                        if mod.type in {"SOLIDIFY", "SCREW", "BOOLEAN"}:
                            new_modifier = temp_obj.modifiers.new(name=mod.name, type=mod.type)
                            for prop in dir(mod):
                                if not prop.startswith("_") and prop not in {
                                    "name",
                                    "type",
                                }:
                                    try:
                                        setattr(new_modifier, prop, getattr(mod, prop))
                                    except AttributeError:
                                        pass  # Skip properties that don't exist

                    # Apply the modifiers
                    u.set_active_object(temp_obj)
                    for mod in temp_obj.modifiers:
                        try:
                            bpy.ops.object.modifier_apply(modifier=mod.name)
                        except Exception as e:
                            print(
                                f"[ERROR] [{_mod}] Error applying modifier '{mod.name}' to temp object '{temp_obj.name}: {e}"
                            )

                    u.deselect_object(temp_obj)
                    break  # Exit the modifiers loop

            # Create a BMesh from the temporary or original mesh
            bm = bmesh.new()
            bm.from_mesh(temp_mesh if temp_mesh else obj.data)
            bm.verts.ensure_lookup_table()

            # Check for non-manifold vertices and faces
            non_manifold_verts = [v for v in bm.verts if not v.is_manifold] if bm.verts else True  # True is Manifold
            faces = [f for f in bm.faces]

            if u.is_debug():
                print(f"[DEBUG] [{_mod}] {obj.name} Vertices: {len(bm.verts)}")
                print(f"[DEBUG] [{_mod}] {obj.name} Non-Manifold: {bool(non_manifold_verts)}")
                print(f"[DEBUG] [{_mod}] {obj.name} Faces: {len(faces)}")

            # Flag the object if it has non-manifold vertices and no faces
            if non_manifold_verts and not faces:
                flagged.append(obj)

            # Clean up temporary objects and meshes
            if temp_obj:
                u.log(f"[INFO] [{_mod}] Deleting temporary object: {temp_obj.name}")
                bpy.data.objects.remove(temp_obj)
            if temp_mesh:
                u.log(f"[INFO] [{_mod}] Deleting temporary mesh: {temp_mesh.name}")
                bpy.data.meshes.remove(temp_mesh)

            bm.free()

        # Process curve objects
        for obj in u.iter_scene_objects(types=[u.OBJECT_TYPES.CURVE]):
            if not u.is_object_visible_in_viewport(obj):
                continue

            u.log(f"[INFO] [{_mod}] Processing curve: {obj.name}")

            # Check if has spline with points
            has_points = False
            splines = obj.data.splines
            if splines:
                for spline in splines:
                    # Check both bezier and nurbs/poly points
                    if len(spline.bezier_points) > 1 or len(spline.points) > 1:
                        has_points = True
                        break

            if u.is_debug():
                print(f"[DEBUG] [{_mod}] {obj.name} Splines: {len(obj.data.splines)}")
                print(f"[DEBUG] [{_mod}] {obj.name} Has Points: {has_points}")

            # Flag the curve if it has no points
            if not has_points:
                flagged.append(obj)

        # Report the results
        msg = f"Found {len(flagged)} potentially invalid objects"
        u.log(f"[INFO] [{_mod}] {msg}")
        for i, flagged_obj in enumerate(flagged, start=1):
            u.log(f"[INFO] [{_mod}] ({i}) {flagged_obj.name}")
            u.select_object(flagged_obj, set_active=(i == 1))

        self.report({"INFO"}, msg)

        return {"FINISHED"}


class SimpleToolbox_OT_SelectNonUniformScaleObjects(bpy.types.Operator):
    bl_label = "Check Non-Uniform Objects"
    bl_idname = "r0tools.select_non_uniform_scale_objects"
    bl_description = "Evaluates which objects in the scene have a non-uniform scale. The comparison threshold tolerance can be adjusted"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT]

    tolerance: FloatProperty(
        name="Tolerance",
        description="Maximum allowed distance from a scale of (1, 1, 1)",
        default=1e-5,
        min=1e-9,
        soft_max=1e2,
        precision=6,
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts

    def execute(self, context):
        target_scale = Vector((1.0, 1.0, 1.0))

        objs_to_select = [
            obj
            for obj in u.iter_scene_objects(types=[u.OBJECT_TYPES.MESH, u.OBJECT_TYPES.CURVE, u.OBJECT_TYPES.SURFACE])
            if (obj.scale - target_scale).length > self.tolerance
        ]

        if not objs_to_select:
            self.report({"INFO"}, "No objects with non-uniform scale found.")
            return {"FINISHED"}

        u.deselect_all()

        for obj in objs_to_select:
            u.select_object(obj, set_active=True)

        self.report({"INFO"}, f"Selected {len(objs_to_select)} objects with non-uniform scale.")
        return {"FINISHED"}


class SimpleToolbox_OT_ClearAxisSharpEdgesX(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_x"
    bl_description = "Clears sharp edges along the X axis"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def execute(self, context):
        u.op_clear_sharp_along_axis("Y")  # Y so as to clear along the axis, not across it
        return {"FINISHED"}


class SimpleToolbox_OT_ClearAxisSharpEdgesY(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_y"
    bl_description = "Clears sharp edges along the Y axis"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def execute(self, context):
        u.op_clear_sharp_along_axis("X")  # X so as to clear along the axis, not across it
        return {"FINISHED"}


class SimpleToolbox_OT_UVCheckIslandThresholds(bpy.types.Operator):
    bl_label = "Check UV Island Sizes"
    bl_idname = "r0tools.uv_check_island_thresholds"
    bl_description = "Iterates over UV Islands of selected objects and selects islands below defined thresholds"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [
        u.OBJECT_MODES.OBJECT,
        u.OBJECT_MODES.EDIT,
        u.OBJECT_MODES.EDIT_MESH,
    ]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def execute(self, context):
        u.log("\n------------- Check UV Islands Size Thresholds -------------")

        addon_props = u.get_addon_props()

        uv_x = u.get_uvmap_size_x()
        uv_y = u.get_uvmap_size_y()

        size_relative_threshold = (
            addon_props.uvisland_sizecheck_arearelative if addon_props.use_uvisland_sizecheck_arearelative else 0
        )
        size_pixel_coverage_threshold = (
            addon_props.uvisland_sizecheck_area_pixelcoverage
            if addon_props.use_uvisland_sizecheck_area_pixelcoverage
            else 0
        )
        size_pixel_coverage_pct_threshold = (
            addon_props.uvisland_sizecheck_area_pixelpercentage
            if addon_props.use_uvisland_sizecheck_area_pixelpercentage
            else 0
        )

        # Store object selection
        original_selection = u.get_selected_objects()
        # Store active object
        original_active = u.get_active_object()
        # Object, Edit Modes?
        original_mode = context.mode
        if original_mode in [u.OBJECT_MODES.EDIT_MESH]:
            # Need to hack edit mode, because there's EDIT and EDIT_MESH...
            original_mode = u.OBJECT_MODES.EDIT

        total_small_islands = 0

        if size_relative_threshold == 0:
            u.log(f"[INFO] [{_mod}] Not using Relative Area Size factor into account.")
        if size_pixel_coverage_threshold == 0:
            u.log(f"[INFO] [{_mod}] Not using Pixel Area Coverage into account.")
        if size_pixel_coverage_pct_threshold == 0:
            u.log(f"[INFO] [{_mod}] Not using Pixel Area Percentage factor into account.")

        # Prepare to go 1 by 1 and select only that object
        u.deselect_all()

        for obj in original_selection:
            if obj.type == u.OBJECT_TYPES.MESH:
                u.select_object(obj, add=False, set_active=True)
                small_islands, small_faces, small_verts = select_small_uv_islands(
                    obj,
                    uv_x,
                    uv_y,
                    threshold=size_relative_threshold,
                    threshold_px_coverage=size_pixel_coverage_threshold,
                    threshold_pct=size_pixel_coverage_pct_threshold,
                )
                total_small_islands += len(small_islands)

        # Restore selection
        for obj in original_selection:
            u.select_object(obj)

        u.set_active_object(original_active)

        # Restore mode
        u.set_object_mode(original_mode)

        report_msg = f"Selected {total_small_islands} small island(s) across {len(original_selection)} object(s)"
        u.log(f"[INFO] [{_mod}] {report_msg}")
        self.report({"INFO"}, report_msg)

        return {"FINISHED"}


class SimpleToolbox_OT_ClearAxisSharpEdgesZ(bpy.types.Operator):
    bl_label = "Clear Sharp X"
    bl_idname = "r0tools.clear_sharp_axis_z"
    bl_description = "Clears sharp edges along the Z axis (XY plane)"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def execute(self, context):
        u.op_clear_sharp_along_axis("Z")  # Z: along the XY axis
        return {"FINISHED"}


# ===================================================================
#   Register & Unregister
# ===================================================================

# fmt: off
classes = [
    SimpleToolbox_OT_ToggleWireDisplay,
    
    VIEW3D_MT_CustomOrientationsPieMenu,
    SimpleToolbox_OT_ShowCustomOrientationsPie,
    TRANSFORM_OT_SetCustomOrientation,
    BUILTINS_OT_IconViewer,
    
    SimpleToolbox_OT_ReloadNamedScripts,
    SimpleToolbox_OT_FixImageDataPaths,
    SimpleToolbox_OT_ClearChildrenRecurse,
    
    SimpleToolbox_OT_FindModifierSearch,
    SimpleToolbox_OT_FindModifierSelectObject,
    SimpleToolbox_OT_FindModifierSelectCategory,
    SimpleToolbox_OT_FindModifierClearList,
    
    SimpleToolbox_OT_RemoveUnusedMaterials,
    
    SimpleToolbox_OT_DissolveNthEdge,
    SimpleToolbox_OT_RestoreNthEdge,
    SimpleToolbox_OT_ResetEdgeData,
    SimpleToolbox_OT_RestoreRotationFromSelection,
    SimpleToolbox_OT_SelectEmptyObjects,SimpleToolbox_OT_SelectNonUniformScaleObjects,
    SimpleToolbox_OT_ClearAxisSharpEdgesX,
    SimpleToolbox_OT_ClearAxisSharpEdgesY,
    SimpleToolbox_OT_ClearAxisSharpEdgesZ,

    SimpleToolbox_OT_UVCheckIslandThresholds,
]
# fmt: on


addon_keymaps = []


def register_keymapping():
    wm = bpy.context.window_manager

    keymap = wm.keyconfigs.addon.keymaps.new(name="3D View", space_type="VIEW_3D")
    keymap_item = keymap.keymap_items.new(
        SimpleToolbox_OT_ShowCustomOrientationsPie.bl_idname, type="NONE", value="PRESS"
    )
    if u.is_debug():
        print(f"[INFO] [{_mod}] Added keymap item: {(keymap, keymap_item)}")
    addon_keymaps.append((keymap, keymap_item))


def unregister_keymapping():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


def register():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    CustomTransformsOrientationsTracker.register_handler()

    _BUILTIN_ORIENTATIONS_PIE.draw = modified_orientations_pie_draw


def unregister():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    CustomTransformsOrientationsTracker.unregister_handler()

    _BUILTIN_ORIENTATIONS_PIE.draw = _ORIGINAL_ORIENTATIONS_PIE_DRAW
