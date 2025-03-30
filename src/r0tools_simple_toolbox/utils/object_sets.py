import bpy

from .. import utils as u


def get_object_sets() -> list:
    addon_props = u.get_addon_props()

    return addon_props.object_sets


def get_object_sets_count() -> int:
    return len(get_object_sets())


def get_active_object_set_index() -> int:
    addon_props = u.get_addon_props()
    active_index = addon_props.object_sets_index

    return active_index


def set_active_object_set_index(index: int):
    addon_props = u.get_addon_props()

    if index < get_object_sets_count():
        addon_props.object_sets_index = index


def get_object_set_at_index(index: int) -> int:
    object_sets = get_object_sets()

    if index < get_object_sets_count():
        return object_sets[index]

    return None


def remove_object_set_at_index(index: int):
    object_sets = get_object_sets()

    if index < get_object_sets_count():
        object_sets.remove(index)


def get_object_set_name_at_index(index: int) -> str:
    object_set = get_object_set_at_index(index)

    if not object_set:
        return ""

    return object_set.name


def set_object_set_name(object_set, new_name) -> bool:
    try:
        object_set.name = new_name
    except Exception as e:
        print(f"[ERROR] [OBJECT_SETS] Unable to rename object set: {e}")
        return False

    return True


def set_object_set_name_at_index(index, new_name) -> bool:
    object_set = get_object_set_at_index(index)

    if object_set:
        object_set.name = new_name
        return True

    return False


def object_set_at_index_update_count(index: int) -> bool:
    object_set = get_object_set_at_index(index)

    if object_set:
        object_set.update_count()
        return True

    return False


def get_object_set_objects_at_index(index: int):
    object_set = get_object_set_at_index(index)

    if object_set:
        return object_set.objects

    return None


def iter_objects_of_object_set_at_index(index: int):
    object_set = get_object_set_at_index(index)

    if object_set:
        for obj_prop in object_set.objects:
            yield obj_prop.object

    return None


def move_object_set_to_index(from_index, to_index):
    object_sets = get_object_sets()

    object_sets.move(from_index, to_index)


def draw_objects_sets_uilist(layout, context, object_sets_box=None):
    """
    Draw the Objects Sets UI list

    Args:
        layout: The layout to draw in
        context: The current context
        object_sets_box: Optional box to draw within
    """
    addon_prefs = u.get_addon_prefs()
    addon_props = u.get_addon_props()

    # Object Sets Editor parent layout
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

    # Object Sets Row Number Slider (Same as in addon preferences)
    row = parent.row()
    row.prop(addon_prefs, "object_sets_list_rows", text="Rows:")

    row = parent.row()
    split = row.split(factor=0.92)  # Affects right side button width

    # Left Section - List
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

    # Right side - Buttons
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

    # Object Sets Actions (Downward arrow HLT dropdown menu)
    col.separator(factor=1.0)  # Spacer
    col.menu("SimpleToolbox_MT_ObjectSetsActionsMenu", text="")

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


def cleanup_object_set_invalid_references(scene):
    """
    Remove invalid object references from object sets

    This cleans up references to deleted objects to prevent errors.
    """
    if u.IS_DEBUG():
        print("------------- Cleanup Object Sets Invalid References -------------")

    addon_props = u.get_addon_props()

    bpy_scene_objects_len = len(bpy.context.scene.objects)
    bpy_data_objects_len = len(bpy.data.objects)
    scene_objects_len = len(addon_props.scene_objects)
    data_objects_len = len(addon_props.data_objects)

    objects_updated = False

    if u.IS_DEBUG():
        print("------------- Update Data Scene Objects -------------")
        print(f"[DEBUG] [OBJECT_SETS] Scene {bpy_scene_objects_len} == {scene_objects_len}")
        print(f"[DEBUG] [OBJECT_SETS] Data  {bpy_data_objects_len} == {data_objects_len}")

    count_changed = bpy_data_objects_len != data_objects_len or bpy_scene_objects_len != scene_objects_len

    if count_changed:
        if u.IS_DEBUG():
            print("------------- Updating Object References -------------")

        objects_updated = True

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

        if unused_objects:
            if u.IS_DEBUG():
                print(f"Unused blocks to be cleared: {len(unused_objects)}")
            for unused in unused_objects:
                if u.IS_DEBUG():
                    print(f"[DEBUG] [OBJECT_SETS] (DATA) {unused.name} not in Scene.")

    if objects_updated:
        for object_set in addon_props.object_sets:
            # Identify invalid objects without modifying anything
            invalid_objects = []
            for object_item in object_set.objects:
                obj = object_item.object
                if not u.is_valid_object_global(obj):
                    invalid_objects.append(obj)

            if invalid_objects:
                for obj in invalid_objects:
                    try:
                        object_set.remove_object(obj)
                    except Exception as e:
                        print(f"[ERROR] Failed to remove object from set: {e}")

                print(f"Cleaned up {len(invalid_objects)} references for Object Set '{object_set.name}'")

        # Reset the flag after cleanup
        objects_updated = False

        # Force UI Update to reflect changes
        for area in bpy.context.screen.areas:
            if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                area.tag_redraw()


@bpy.app.handlers.persistent
def refresh_object_sets_colours(context):
    """Refresh colors for all object sets"""
    if u.IS_DEBUG():
        print("[OBJECT_SETS] Force Refreshing Object Sets' Colours")
    addon_prefs = u.get_addon_prefs()
    object_sets = get_object_sets()

    if not addon_prefs.object_sets_use_colour:
        return

    for object_set in object_sets:
        if u.IS_DEBUG():
            print(f"[DEBUG] Refresh: {object_set.name}")
        object_set.update_object_set_colour(context)
