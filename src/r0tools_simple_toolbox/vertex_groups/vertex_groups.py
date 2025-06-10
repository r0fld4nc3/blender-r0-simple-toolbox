import bpy

from .. import utils as u
from ..defines import TOOLBOX_PROPS_NAME

_mod = "VERTEX_GROUPS"


def get_vertex_groups():
    addon_props = u.get_addon_props()

    if not addon_props:
        return None

    return addon_props.vertex_groups


def get_vertex_groups_count() -> int:
    return len(get_vertex_groups())


def get_vertex_group_at_index(index: int) -> int:
    vertex_groups = get_vertex_groups()

    if index < get_vertex_groups_count():
        return vertex_groups[index]

    return None


def get_selected_vgroups() -> list:
    vertex_groups = get_vertex_groups()

    if not vertex_groups:
        return []

    return [item for item in vertex_groups if item.selected]


def set_vertex_group_locked(vertex_group):
    vertex_group.locked = True

    return True


def set_vertex_group_unlocked(vertex_group):
    vertex_group.locked = False

    return False


def get_selected_vgroups_names() -> list:
    vertex_groups = get_vertex_groups()

    if not vertex_groups:
        return []

    return [item.name for item in vertex_groups if item.selected]


def get_active_vertex_group_index() -> int:
    addon_props = u.get_addon_props()

    if not addon_props:
        return -1

    active_index = addon_props.vertex_group_list_index

    return active_index


def set_vertex_groups_depsgraph_do_update(do_update=True):
    addon_props = u.get_addon_props()

    if not addon_props:
        return False

    addon_props.vgroups_do_update = do_update


def get_vertex_groups_lock_states():
    addon_props = u.get_addon_props()

    if not addon_props:
        return None

    return addon_props.vertex_groups_lock_states


def iter_vertex_groups_lock_states():
    for state in get_vertex_groups_lock_states():
        yield state


def vertex_groups_lock_states_remove_at_index(index: int):
    states = get_vertex_groups_lock_states()
    states.remove(index)


def vertex_groups_cleanup_lock_states():
    addon_props = u.get_addon_props()

    if not addon_props:
        return None

    vertex_groups_names_sorted = sorted([vgroup.name for vgroup in get_vertex_groups()])

    # Cleanup the persistent lock state group
    indices_to_clear = []
    for i, state in enumerate(iter_vertex_groups_lock_states()):
        if state.name not in vertex_groups_names_sorted:
            indices_to_clear.append(i)

    for index in sorted(indices_to_clear, reverse=True):
        states = get_vertex_groups_lock_states()
        states.remove(index)


def _vertex_groups_store_states() -> dict:
    addon_props = u.get_addon_props()

    # Store the current selection state of Vertex Groups List
    selection_state = {}

    for item in addon_props.vertex_groups:
        selection_state[item.name] = {"selected": item.selected, "locked": item.locked}

    return selection_state


def vertex_groups_list_add_groups(props: dict, selection_state: dict):
    addon_props = u.get_addon_props()

    # Populate the UIList
    for prop_name, count in props.items():
        try:
            item = addon_props.vertex_groups.add()
            item.name = prop_name
            item.count = count

            # Restore selection state if it exists
            if prop_name in selection_state:
                item.selected = selection_state[prop_name]["selected"]
                item.locked = selection_state[prop_name]["locked"]
            else:
                # Check persistent states if not in selection state
                for state in iter_vertex_groups_lock_states():
                    if state.name == prop_name:
                        item.locked = state.locked
                        break
        except Exception as e:
            print(f"[ERROR] [{_mod}] Error adding unique Custom Properties: {e}")
            u.context_error_debug(error=e)


def vertex_groups_list_update(scene, context):
    if not u.is_writing_context_safe(scene, check_addon_props=True):
        return None

    addon_props = u.get_addon_props()

    if not addon_props.vgroups_do_update:
        return None

    if not addon_props.show_vertex_groups:
        # Skip update if panel is not visible
        return None

    if bpy.context.selected_objects:
        if u.IS_DEBUG():
            print("------------- Vertex Groups List Update -------------")

        # Store the current selection state before clearing the list
        selection_state = _vertex_groups_store_states()

        try:
            addon_props.vertex_groups.clear()
        except Exception as e:
            print(f"[WARNING] [{_mod}] Property 'vertex_groups' is not writable for '.clear()'. Skipping.")
            if u.IS_DEBUG():
                print(f"[DEBUG] [{_mod}] {e}")
            return None

        # Add vertex groups names to set
        vertex_groups_names_count_usorted = {}  # Unsorted
        for obj in u.iter_scene_objects(selected=True):
            vertex_groups = obj.vertex_groups
            # Object Properties
            for vgroup in vertex_groups:
                vgroup_name = vgroup.name
                if vgroup_name in vertex_groups_names_count_usorted:
                    vertex_groups_names_count_usorted[vgroup_name] += 1
                else:
                    vertex_groups_names_count_usorted[vgroup_name] = 1

        # Sort the dictionary by insertion order
        # For that we get a sorted list of keys and then re-insert with order preservation
        # Incurs a little overhead but could be a nice-to-have
        _sorted_keys = sorted(vertex_groups_names_count_usorted.keys())
        vertex_groups_names_count_sorted = {  # Sorted
            key: vertex_groups_names_count_usorted.get(key) for key in _sorted_keys
        }

        # Populate the UIList
        vertex_groups_list_add_groups(vertex_groups_names_count_sorted, selection_state)

        vertex_groups_cleanup_lock_states()

        # Force UI update
        for area in bpy.context.screen.areas:
            if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                area.tag_redraw()

    else:
        # Store the states even if nothing selected
        selection_state = _vertex_groups_store_states()

        # Clear the property list if no objects are selected
        try:
            addon_props.vertex_groups.clear()
            if u.IS_DEBUG():
                print(f"[DEBUG] [{_mod}] Cleared UIList vertex_groups")
        except Exception as e:
            print(f"[ERROR] [{_mod}] Error clearing vertex groups list when no selected objects: {e}")
            u.context_error_debug(error=e)

        # Force UI update
        if bpy.context.screen:
            if hasattr(bpy.context.screen, "areas"):
                for area in bpy.context.screen.areas:
                    if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                        area.tag_redraw()

    return None


def vertex_group_add(obj: bpy.types.Object, vg_name: str):
    accepted_types = [u.OBJECT_TYPES.MESH]

    if obj.type not in accepted_types:
        return

    obj_vgroup_names = [vgroup.name for vgroup in obj.vertex_groups]

    if vg_name not in obj_vgroup_names:
        obj.vertex_groups.new(name=vg_name)


def iter_obj_vertex_groups(obj):
    for vertex_group in obj.vertex_groups:
        yield vertex_group


def set_obj_active_vertex_group_index(obj, vertex_group: int) -> bool:
    if vertex_group.index < len(obj.vertex_groups):
        obj.vertex_groups.active_index = vertex_group.index
        return True

    return False


def draw_vertex_groups_uilist(layout, context, vertex_groups_box=None):
    from ..menus import SimpleToolbox_MT_VertexGroupsActionsMenu
    from .operators import (
        SimpleToolbox_OT_VgroupsAddPopup,
        SimpleToolbox_OT_VgroupsAssignVertices,
        SimpleToolbox_OT_VgroupsDeselectVertices,
        SimpleToolbox_OT_VgroupsKeepSelected,
        SimpleToolbox_OT_VgroupsRemoveHighlighted,
        SimpleToolbox_OT_VgroupsRemoveSelected,
        SimpleToolbox_OT_VgroupsSelectObjectsWithVgroups,
        SimpleToolbox_OT_VgroupsSelectVertices,
        SimpleToolbox_OT_VgroupsUnassignVertices,
    )

    addon_prefs = u.get_addon_prefs()
    addon_props = u.get_addon_props()

    # Object Sets Editor parent layout
    if vertex_groups_box:
        parent = vertex_groups_box
    elif layout:
        parent = layout
    else:
        print(f"[ERROR] [{_mod}] No valid layout to use:\n{layout=}\n{vertex_groups_box=}")
        return False

    # Vertex Groups Row Number Slider
    row = parent.row()
    split = row.split(factor=0.35)
    col = split.column()
    col.prop(addon_prefs, "vertex_groups_list_rows", text="Rows:")
    col = split.column()
    col.separator()

    row = parent.row()
    split = row.split(factor=0.92)

    # Left Section - List
    col = split.column()
    col.template_list(
        "R0PROP_UL_VertexGroupsList",
        "vertex_groups",
        addon_props,
        "vertex_groups",
        addon_props,
        "vertex_group_list_index",
        rows=addon_prefs.vertex_groups_list_rows,
    )

    # Right Side - Buttons
    col = split.column(align=True)
    col.operator(SimpleToolbox_OT_VgroupsAddPopup.bl_idname, text="+")
    col.operator(SimpleToolbox_OT_VgroupsRemoveHighlighted.bl_idname, text="-")

    # Vertex Groups Actions (Downward arrow dropdown menu)
    col.separator(factor=1.0)  # Spacer
    col.menu(SimpleToolbox_MT_VertexGroupsActionsMenu.bl_idname, text="")

    # Bottom
    # Assign/Unassign Vertices
    if (
        context.mode in u.OBJECT_MODES.EDIT_MESH
        and len(context.selected_objects) > 0
        and u.get_vertex_groups_count() > 0
    ):
        col = parent.column()
        split = col.split(factor=0.5)
        # Assign/Unassign
        row = split.row(align=True)
        row.operator(SimpleToolbox_OT_VgroupsAssignVertices.bl_idname)
        row.operator(SimpleToolbox_OT_VgroupsUnassignVertices.bl_idname)
        # Select/Deselect
        row = split.row(align=True)
        row.operator(SimpleToolbox_OT_VgroupsSelectVertices.bl_idname)
        row.operator(SimpleToolbox_OT_VgroupsDeselectVertices.bl_idname)

        row = parent.row()
        row.prop(bpy.context.scene.tool_settings, "vertex_group_weight")

        # Separator
        row = parent.row()
        row.separator(factor=1.0)

    # Remove Selected Vgroups
    row = parent.row(align=True)
    row.operator(SimpleToolbox_OT_VgroupsRemoveSelected.bl_idname)
    row.operator(SimpleToolbox_OT_VgroupsKeepSelected.bl_idname)

    row = parent.row(align=True)
    row.operator(SimpleToolbox_OT_VgroupsSelectObjectsWithVgroups.bl_idname)

    # MESH_MT_vertex_group_context_menu
