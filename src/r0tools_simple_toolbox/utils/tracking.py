import bpy

from .constants import CUSTOM_PROPERTIES_TYPES
from .context import get_addon_props
from .general import (
    IS_DEBUG,
    context_error_debug,
    is_valid_object_global,
    iter_scene_objects,
)
from .handlers import queue_op


def continuous_property_list_update(scene, context, force_run=False):
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
        prev_selection = (
            set(addon_props.last_object_selection.split(",")) if addon_props.last_object_selection else set()
        )

        if current_selection == prev_selection and not force_run:
            if IS_DEBUG():
                print("[DEBUG] Object selection unchanged; skipping property list update.")
            return None

        if IS_DEBUG():
            print("------------- Continuous Property List Update -------------")

        # Queue the property list update
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
                    if not prop_name.startswith("_") and prop_name not in unique_object_data_props:
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
                        if not prop_name.startswith("_") and prop_name not in unique_mesh_data_props:
                            try:
                                unique_mesh_data_props.add(prop_name)
                                item = addon_props.custom_property_list.add()
                                item.name = prop_name
                                item.type = CUSTOM_PROPERTIES_TYPES.MESH_DATA
                            except Exception as e:
                                print(f"[ERROR] Error adding unique Object Data Custom Properties: {e}")
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

        queue_op(clear_property_list)

    return None


def update_data_scene_objects(scene, force_run=False):
    """
    Update tracking of objects in the scene and data

    This handler monitors changes to scene objects and
    updates internal references accordingly.
    """
    addon_props = get_addon_props()

    # Get current counts
    bpy_scene_objects_len = len(bpy.context.scene.objects)
    bpy_data_objects_len = len(bpy.data.objects)
    scene_objects_len = len(addon_props.scene_objects)
    data_objects_len = len(addon_props.data_objects)

    if IS_DEBUG():
        print("------------- Update Data Scene Objects -------------")
        print(f"[DEBUG] Scene {bpy_scene_objects_len} == {scene_objects_len}")
        print(f"[DEBUG] Data  {bpy_data_objects_len} == {data_objects_len}")

    # Check if counts have changed
    counts_changed = bpy_data_objects_len != data_objects_len or bpy_scene_objects_len != scene_objects_len

    if force_run or counts_changed:

        def update_object_references():
            if IS_DEBUG():
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

            # Collect Data Objects
            unused_objects = []
            for obj in bpy.data.objects:
                if obj.name in bpy.context.scene.objects:
                    item = addon_props.data_objects.add()
                    item.object = obj
                else:
                    unused_objects.append(obj)

            if IS_DEBUG() and unused_objects:
                print(f"Unused blocks to be cleared: {len(unused_objects)}")
                for unused in unused_objects:
                    print(f"[DEBUG] (DATA) {unused.name} not in Scene.")

        queue_op(update_object_references)
    else:
        # Reset the flag if no changes
        queue_op(lambda: setattr(addon_props, "objects_updated", False))


def cleanup_object_set_invalid_references(scene):
    """
    Remove invalid object references from object sets

    This cleans up references to deleted objects to prevent errors.
    """
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

                    print(f"Cleaned up {len(invalid_objects)} references for Object Set '{object_set.name}'")

                queue_op(remove_invalid_objects, object_set, invalid_objects)

        # Reset the flag after cleanup
        queue_op(lambda: setattr(addon_props, "objects_updated", False))

    # Force UI Update to reflect changes
    for area in bpy.context.screen.areas:
        if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
            area.tag_redraw()
