import time

import bpy

from .. import utils as u
from ..defines import TOOLBOX_PROPS_NAME

_mod = "VERTEX_GROUPS"

# ===============
# === CACHING ===
# ===============
_vertex_groups_cache = {}
_selected_objects_hash = 0
_last_update_time = 0


def get_vertex_groups():
    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    if not addon_vertex_groups_props:
        return None

    return addon_vertex_groups_props.vertex_groups


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
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Vertex Groups Set Locked: Unsafe Context.")
        return None

    vertex_group.locked = True

    return True


def set_vertex_group_unlocked(vertex_group):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Vertex Groups Set Unlocked: Unsafe Context.")
        return None

    vertex_group.locked = False

    return False


def get_selected_vgroups_names() -> list:
    vertex_groups = get_vertex_groups()

    if not vertex_groups:
        return []

    return [item.name for item in vertex_groups if item.selected]


def get_active_vertex_group_index() -> int:
    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    if not addon_vertex_groups_props:
        return -1

    active_index = addon_vertex_groups_props.vertex_group_list_index

    return active_index


def set_vertex_groups_depsgraph_do_update(do_update=True):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Set Vertex Groups Depsgraph Do Update: Unsafe Context.")
        return None

    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    if not addon_vertex_groups_props:
        return False

    addon_vertex_groups_props.vgroups_do_update = do_update


def get_vertex_groups_lock_states():
    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    if not addon_vertex_groups_props:
        return None

    return addon_vertex_groups_props.vertex_groups_lock_states


def set_vertex_group_highlighted_by_name(vertex_group_name: str) -> int:
    """
    Set vertex group to be highlighted (same as clicked to select) in the UIList.

    Returns `index` if succesful, `-1` if name was not found
    """
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Set Vertex Groups Highlighted By Name: Unsafe Context.")
        return None

    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    vertex_groups = get_vertex_groups()

    if not vertex_groups:
        return -1

    for i, vgroup in enumerate(vertex_groups):
        if vgroup.name == vertex_group_name:
            addon_vertex_groups_props.vertex_group_list_index = i
            return i

    return -1


def iter_vertex_groups_lock_states():
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Vertex Groups Iter Lock States: Unsafe Context.")
        return None

    for state in get_vertex_groups_lock_states():
        yield state


def vertex_groups_lock_states_remove_at_index(index: int):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Vertex Groups Lock States Remove At Index: Unsafe Context.")
        return None

    states = get_vertex_groups_lock_states()
    states.remove(index)


def vertex_groups_cleanup_lock_states():
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Vertex Groups Cleanup Lock States: Unsafe Context.")
        return None

    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    if not addon_vertex_groups_props:
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
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Vertex Groups Store States: Unsafe Context.")
        return None

    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    # Store the current selection state of Vertex Groups List
    selection_state = {}

    for item in addon_vertex_groups_props.vertex_groups:
        selection_state[item.name] = {"selected": item.selected, "locked": item.locked}

    return selection_state


def vertex_groups_list_add_groups(props: dict, selection_state: dict):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Vertex Groups List Add Groups: Unsafe Context.")
        return None

    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    # Populate the UIList
    for prop_name, count in props.items():
        try:
            item = addon_vertex_groups_props.vertex_groups.add()
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


def _needs_update():
    global _selected_objects_hash, _last_update_time

    current_time = time.time()
    if current_time - _last_update_time < 0.1:
        return False

    current_hash = u.get_selected_objects_hash()
    if current_hash != _selected_objects_hash:
        _selected_objects_hash = current_hash
        _last_update_time = current_time
        return True

    return False


def vertex_groups_list_update(force: bool = False):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Vertex Groups List Update: Unsafe Context.")
        return None

    addon_props = u.get_addon_props()
    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    if not force:
        if not addon_vertex_groups_props.vgroups_do_update:
            return None

        # Check if update is required
        if not _needs_update():
            return None

    if not addon_props.cat_show_vertex_groups_editor or not addon_props.show_vertex_groups:
        # Skip update if panel is not visible
        return None

    global _vertex_groups_cache

    if u.get_selected_objects():
        if u.IS_DEBUG():
            print("------------- Vertex Groups List Update -------------")

        # Calculate new vertex groups data
        vertex_groups_new = {}
        for obj in u.iter_scene_objects(selected=True):
            for vgroup in obj.vertex_groups:
                vgroup_name = vgroup.name
                vertex_groups_new[vgroup_name] = vertex_groups_new.get(vgroup.name, 0) + 1

        # Check if data really changed
        if vertex_groups_new == _vertex_groups_cache:
            return None

        # Store the current selection state before clearing the list
        selection_state = _vertex_groups_store_states()

        try:
            addon_vertex_groups_props.vertex_groups.clear()
        except Exception as e:
            print(f"[WARNING] [{_mod}] Property 'vertex_groups' is not writable for '.clear()'. Skipping.")
            if u.IS_DEBUG():
                print(f"[DEBUG] [{_mod}] {e}")
            return None

        # Sort and add groups (only when changed)
        sorted_groups = dict(sorted(vertex_groups_new.items()))
        vertex_groups_list_add_groups(sorted_groups, selection_state)

        # Update the cache
        _vertex_groups_cache = vertex_groups_new

        # Cleanup only when needed
        if len(vertex_groups_new) != len(addon_vertex_groups_props.vertex_groups):
            vertex_groups_cleanup_lock_states()

        # UI update
        u.tag_redraw_if_visible()

    else:
        if _vertex_groups_cache:
            # Store the states
            selection_state = _vertex_groups_store_states()

            # Clear the property list if no objects are selected
            try:
                addon_vertex_groups_props.vertex_groups.clear()
                _vertex_groups_cache = {}
                if u.IS_DEBUG():
                    print(f"[DEBUG] [{_mod}] Cleared UIList vertex_groups")
            except Exception as e:
                print(f"[ERROR] [{_mod}] Error clearing vertex groups list when no selected objects: {e}")
                u.context_error_debug(error=e)

            # UI update
            u.tag_redraw_if_visible()

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


def set_obj_active_vertex_group(obj, vertex_group) -> bool:
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
        SimpleToolbox_OT_VgroupsRefresh,
        SimpleToolbox_OT_VgroupsRemoveHighlighted,
        SimpleToolbox_OT_VgroupsRemoveSelected,
        SimpleToolbox_OT_VgroupsSelectObjectsWithVgroups,
        SimpleToolbox_OT_VgroupsSelectVertices,
        SimpleToolbox_OT_VgroupsUnassignVertices,
    )

    addon_prefs = u.get_addon_prefs()
    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

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
        addon_vertex_groups_props,
        "vertex_groups",
        addon_vertex_groups_props,
        "vertex_group_list_index",
        rows=addon_prefs.vertex_groups_list_rows,
    )

    # Right Side - Buttons
    col = split.column(align=True)
    col.operator(SimpleToolbox_OT_VgroupsAddPopup.bl_idname, text="+")
    col.operator(SimpleToolbox_OT_VgroupsRemoveHighlighted.bl_idname, text="-")

    col.separator(factor=1.0)
    col.operator(SimpleToolbox_OT_VgroupsRefresh.bl_idname, icon="FILE_REFRESH")

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
