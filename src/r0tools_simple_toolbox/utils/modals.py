import bpy

from r0tools_simple_toolbox import utils as u

_UPDATE_INTERVAL = 0.5


def is_modal_running(op_name: str):
    return any(op.bl_idname == op_name for op in bpy.context.window_manager.operators)


# Unused but left for possible later purpose if needed
class SimpleToolbox_OT_MonitorSceneDataObjectsCleanup(bpy.types.Operator):
    bl_idname = "r0tools.modals_monitor_scene_data_objects_cleanup"
    bl_label = "Flurp"

    _timer = None

    @classmethod
    def poll(cls, context):
        return context is not None and context.scene is not None

    def modal(self, context, event):
        """
        Update tracking of objects in the scene and data

        This handler monitors changes to scene objects and
        updates internal references accordingly.
        """

        if event.type == "TIMER":
            if u.IS_DEBUG():
                print("[DEBUG] [MODALS] Timer tick received")
            try:
                addon_props = u.get_addon_props()

                # Get current counts
                bpy_scene_objects_len = len(bpy.context.scene.objects)
                bpy_data_objects_len = len(bpy.data.objects)
                scene_objects_len = len(addon_props.scene_objects)
                data_objects_len = len(addon_props.data_objects)

                if u.IS_DEBUG():
                    print("------------- Update Data Scene Objects -------------")
                    print(f"[DEBUG] Scene {bpy_scene_objects_len} == {scene_objects_len}")
                    print(f"[DEBUG] Data  {bpy_data_objects_len} == {data_objects_len}")

                # Check if counts have changed
                counts_changed = bpy_data_objects_len != data_objects_len or bpy_scene_objects_len != scene_objects_len

                if counts_changed:
                    self.update_collect_references()

                    # Collect Data Objects
                    unused_objects = []
                    for obj in bpy.data.objects:
                        if obj.name in bpy.context.scene.objects:
                            item = addon_props.data_objects.add()
                            item.object = obj
                        else:
                            unused_objects.append(obj)

                    if unused_objects:
                        if u.IS_DEBUG():
                            print(f"Unused blocks to be cleared: {len(unused_objects)}")
                        for unused in unused_objects:
                            if u.IS_DEBUG():
                                print(f"[DEBUG] (DATA) {unused.name} not in Scene.")

                    u.cleanup_object_set_invalid_references(context.scene)

            except Exception as e:
                print(f"[ERROR] Object reference update error: {str(e)}")

        return {"PASS_THROUGH"}

    def execute(self, context):
        # Set up timer for continuous monitoring
        # Check if it is not running first
        if not is_modal_running("r0tools.modals_monitor_scene_data_objects_cleanup"):
            u.cleanup_object_set_invalid_references(context.scene)

            wm = context.window_manager
            self._timer = wm.event_timer_add(_UPDATE_INTERVAL, window=context.window)

            # Register modal handler
            wm.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def update_collect_references(self):
        addon_props = u.get_addon_props()

        if u.IS_DEBUG():
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

    def cancel(self, context):
        if u.IS_DEBUG():
            print("[DEBUG] [MODALS] Cancel Monitor Scene Data Objects Cleanup")
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
        return None


# Unused but left for possible later purpose if needed
class SimpleToolbox_OT_MonitorPropertyListUpdates(bpy.types.Operator):
    bl_idname = "r0tools.modals_continuous_property_list_update"
    bl_label = "Monitor Property List Updates"
    bl_description = "Continuously monitor object selection and update property lists"

    _timer = None

    @classmethod
    def poll(cls, context):
        return context is not None and context.scene is not None

    def modal(self, context, event):
        """
        Continuously update property list based on selected objects

        This modal operator monitors object selection changes and
        updates the custom property list accordingly.
        """
        if event.type == "TIMER":
            try:
                addon_props = u.get_addon_props()

                # Skip update if panel is not visible
                if not addon_props.show_custom_property_list_prop:
                    if u.IS_DEBUG():
                        print("[DEBUG] Custom Properties Panel is not visible, skipping update.")
                    return {"PASS_THROUGH"}

                # Get current selection
                current_selection = {obj.name for obj in u.iter_scene_objects(selected=True)}
                prev_selection = (
                    set(addon_props.last_object_selection.split(",")) if addon_props.last_object_selection else set()
                )

                # Check if selection changed
                if current_selection != prev_selection:
                    if u.IS_DEBUG():
                        print("------------- Continuous Property List Update -------------")
                        print(f"[DEBUG] Selection changed: {prev_selection} -> {current_selection}")

                    # Selection exists, update property list
                    if current_selection:
                        self.update_property_list(context, current_selection)
                    else:
                        self.clear_property_list(context)

            except Exception as e:
                print(f"[ERROR] Property list update error: {str(e)}")

        return {"PASS_THROUGH"}

    def update_property_list(self, context, current_selection):
        """Update the property list with properties from selected objects"""
        addon_props = u.get_addon_props()

        try:
            # Clear existing list
            addon_props.custom_property_list.clear()

            # Add unique custom properties to the set
            unique_object_data_props = set()
            unique_mesh_data_props = set()

            for obj in context.selected_objects:
                # Object Properties
                for prop_name in obj.keys():
                    if u.IS_DEBUG():
                        print(f"[DEBUG] (OP) {obj.name} - {prop_name=}")
                    if not prop_name.startswith("_") and prop_name not in unique_object_data_props:
                        try:
                            unique_object_data_props.add(prop_name)
                            item = addon_props.custom_property_list.add()
                            item.name = prop_name
                            # Type is defaulted to Object
                        except Exception as e:
                            print(f"[ERROR] Error adding unique Custom Properties: {e}")
                            u.context_error_debug(error=e)

                # Object Data Properties
                if obj.data and obj.type == "MESH":
                    for prop_name in obj.data.keys():
                        if u.IS_DEBUG():
                            print(f"[DEBUG] (ODP) {obj.name} - {prop_name=}")
                        if not prop_name.startswith("_") and prop_name not in unique_mesh_data_props:
                            try:
                                unique_mesh_data_props.add(prop_name)
                                item = addon_props.custom_property_list.add()
                                item.name = prop_name
                                item.type = u.CUSTOM_PROPERTIES_TYPES.MESH_DATA
                            except Exception as e:
                                print(f"[ERROR] Error adding unique Object Data Custom Properties: {e}")
                                u.context_error_debug(error=e)

            # Update the last object selection
            addon_props.last_object_selection = ",".join(current_selection)

            # Force UI update
            self.redraw_ui()

        except Exception as e:
            print(f"[ERROR] Error updating property list: {e}")
            u.context_error_debug(error=e)

    def clear_property_list(self, context):
        """Clear property list when no objects are selected"""
        addon_props = u.get_addon_props()

        try:
            addon_props.custom_property_list.clear()
            if u.IS_DEBUG():
                print(f"Cleared UIList custom_property_list")
        except Exception as e:
            print(f"[ERROR] Error clearing custom property list when no selected objects: {e}")
            u.context_error_debug(error=e)

        try:
            addon_props.last_object_selection = ""
            if u.IS_DEBUG():
                print(f"Cleared property last_object_selection")
        except Exception as e:
            print(f"[ERROR] Error setting last object selection when no selected objects: {e}")
            u.context_error_debug(error=e)

        # Force UI update
        self.redraw_ui()

    def redraw_ui(self):
        """Force UI areas to redraw"""
        for area in bpy.context.screen.areas:
            if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                area.tag_redraw()

    def execute(self, context):
        """Start the modal operator"""
        # Check if already running
        if not is_modal_running("r0tools.modals_continuous_property_list_update"):
            # Do initial update
            current_selection = {obj.name for obj in u.iter_scene_objects(selected=True)}

            if current_selection:
                self.update_property_list(context, current_selection)
            else:
                self.clear_property_list(context)

            # Set up timer for continuous monitoring
            wm = context.window_manager
            self._timer = wm.event_timer_add(_UPDATE_INTERVAL, window=context.window)

            # Register modal handler
            wm.modal_handler_add(self)

            if u.IS_DEBUG():
                print("[DEBUG] Started property list monitoring")

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        """Clean up when the operator is cancelled"""
        if u.IS_DEBUG():
            print("[DEBUG] Cancelling property list monitor")

        if self._timer:
            context.window_manager.event_timer_remove(self._timer)

        return None


@bpy.app.handlers.persistent
def delayed_startup(dummy):
    try:
        """
        if not is_modal_running("r0tools.modals_monitor_scene_data_objects_cleanup"):
            print("[MODALS] Starting Modal Monitor Scene Data Objects Cleanup...")
            bpy.ops.r0tools.modals_monitor_scene_data_objects_cleanup()
            print("[MODALS] Modal Monitor Scene Data Objects Cleanup started successfully")
        else:
            print("[MODALS] Modal Monitor Scene Data Objects Cleanup already running...")
        """

        """
        if not is_modal_running("r0tools.modals_continuous_property_list_update"):
            print("[MODALS] Starting Modal Continuous Property List Update...")
            bpy.ops.r0tools.modals_continuous_property_list_update()
            print("[MODALS] Modal Continuous Property List Update started successfully")
        else:
            print("[MODALS] Modal Continuous Property List Update already running...")
        """

    except Exception as e:
        print(f"[ERROR] Failed to start modal: {e}")
        return 1.0
    return None


classes = []

load_post_handlers = [delayed_startup]


def register():
    for cls in classes:
        print(f"[MODALS] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    for handler in load_post_handlers:
        print(f"[MODALS] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        print(f"[MODALS] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        print(f"[MODALS] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)
