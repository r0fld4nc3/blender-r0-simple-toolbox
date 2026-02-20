import logging
import time

import bpy

from .. import utils as u

log = logging.getLogger(__name__)

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
    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    if not addon_vertex_groups_props:
        return -1

    active_index = addon_vertex_groups_props.vertex_group_list_index

    return active_index


def set_vertex_groups_depsgraph_do_update(do_update=True):
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
    for state in get_vertex_groups_lock_states():
        yield state


def vertex_groups_lock_states_remove_at_index(index: int):
    states = get_vertex_groups_lock_states()
    states.remove(index)


def vertex_groups_cleanup_lock_states():
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


def vertex_groups_list_add_groups(props: dict, selection_state: dict):
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
            log.error(f"Error popualting UIList: {e}")
            u.context_error_debug(error=e)


def _vertex_groups_store_states() -> dict:
    addon_vertex_groups_props = u.get_addon_vertex_groups_props()

    # Store the current selection state of Vertex Groups List
    selection_state = {}

    for item in addon_vertex_groups_props.vertex_groups:
        selection_state[item.name] = {"selected": item.selected, "locked": item.locked}

    return selection_state


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


def vertex_groups_list_update(scene=None, force: bool = False):
    log.debug(f"vertex_groups_list_update(scene = {scene}, force = {force})")

    scene = u.get_scene(scene)

    addon_props = u.get_addon_props(scene)
    addon_vertex_groups_props = u.get_addon_vertex_groups_props(scene)

    # Skip if addon props is not available
    if not addon_props:
        return None

    # Skip if addon vertex props is not available
    if not addon_vertex_groups_props:
        return None

    # Skip update if panel is not visible and not forcing update
    if not addon_props.cat_show_vertex_groups_editor and not force:
        return None

    if not force:
        if not addon_vertex_groups_props.vgroups_do_update:
            return None

        # Check if update is required
        if not _needs_update():
            return None

    global _vertex_groups_cache

    if u.get_selected_objects():
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

        safe_clear_vertex_groups_collection(scene)

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
                safe_clear_vertex_groups_collection(scene)
                _vertex_groups_cache = {}
                log.debug(f"[DEBUG] Cleared UIList vertex_groups")
            except Exception as e:
                log.error(f"Error clearing vertex groups list when no selected objects: {e}")
                u.context_error_debug(error=e)

            # UI update
            u.tag_redraw_if_visible()
    return None


def safe_clear_vertex_groups_collection(scene):
    addon_vertex_groups_props = u.get_addon_vertex_groups_props(scene)

    was_updating_before = u.is_updating()

    if not was_updating_before:
        u.set_is_updating(True)

    try:
        while len(addon_vertex_groups_props.vertex_groups) > 0:
            addon_vertex_groups_props.vertex_groups.remove(len(addon_vertex_groups_props.vertex_groups) - 1)
        return True
    except Exception as e:
        log.error(f"Failed to clear vertex groups: {e}")
        return False
    finally:
        if not was_updating_before:
            u.set_is_updating(False)


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


def set_obj_active_vertex_group(obj, vertex_group_name: str) -> bool:
    vgroup_index = obj.vertex_groups.find(vertex_group_name)
    if vgroup_index != -1:
        obj.vertex_groups.active_index = vgroup_index
        return True

    return False


def _vertex_group_sync_selection(self, context):
    prop_sync_selection = self.sync_selection

    if not prop_sync_selection:
        return

    if not self.vertex_groups or self.vertex_group_list_index >= len(self.vertex_groups):
        return

    # Name of vgroup
    selected_vgroup = get_vertex_group_at_index(self.vertex_group_list_index)
    vgroup_name = selected_vgroup.name

    # Propagate active vgroup to object selection
    for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
        obj_vgroups = obj.vertex_groups

        if vgroup_name not in obj_vgroups:
            continue

        set_obj_active_vertex_group(obj, vgroup_name)


def draw_vertex_groups_uilist(layout, context):
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

    scene = context.scene
    scene_tool_settings = scene.tool_settings

    # Vertex Groups Row Number Slider
    row = layout.row()
    col_left = row.column()
    col_left.alignment = "LEFT"
    col_left.prop(addon_vertex_groups_props, "vertex_groups_list_rows", text="Rows:")
    col_right = row.column()
    col_right.separator()

    row = layout.row()  # Spacer

    # Sync Selection
    col_left = row.column()
    col_left.alignment = "LEFT"
    col_left.prop(addon_vertex_groups_props, "sync_selection", icon="UV_SYNC_SELECT")
    col_right = row.column()
    col_right.separator()

    row = layout.row()  # Spacer

    # Auto-Normalize
    if scene_tool_settings:
        col_left = row.column()
        col_left.prop(scene_tool_settings, "use_auto_normalize", text="Auto-Normalize")

    row = layout.row()  # Spacer

    # Left Section - List
    col_left = row.column()
    col_left.template_list(
        "R0PROP_UL_VertexGroupsList",
        "vertex_groups",
        addon_vertex_groups_props,
        "vertex_groups",
        addon_vertex_groups_props,
        "vertex_group_list_index",
        rows=addon_vertex_groups_props.vertex_groups_list_rows,
    )

    # Right Side - Buttons
    col_right = row.column(align=True)
    col_right.alignment = "RIGHT"
    col_right.scale_x = addon_prefs.OPERATOR_COLUMN_SIZE_X
    col_right.operator(SimpleToolbox_OT_VgroupsAddPopup.bl_idname, text="+")
    col_right.operator(SimpleToolbox_OT_VgroupsRemoveHighlighted.bl_idname, text="-")

    col_right.separator(factor=1.0)
    col_right.operator(SimpleToolbox_OT_VgroupsRefresh.bl_idname, icon="FILE_REFRESH", text="")

    # Vertex Groups Actions (Downward arrow dropdown menu)
    col_right.separator(factor=1.0)  # Spacer
    col_right.menu(SimpleToolbox_MT_VertexGroupsActionsMenu.bl_idname, text="")

    # Bottom
    # Assign/Unassign Vertices
    if (
        context.mode in u.OBJECT_MODES.EDIT_MESH
        and len(context.selected_objects) > 0
        and u.get_vertex_groups_count() > 0
    ):
        col = layout.column()
        split = col.split(factor=0.5)
        # Assign/Unassign
        row = split.row(align=True)
        row.operator(SimpleToolbox_OT_VgroupsAssignVertices.bl_idname)
        row.operator(SimpleToolbox_OT_VgroupsUnassignVertices.bl_idname)
        # Select/Deselect
        row = split.row(align=True)
        row.operator(SimpleToolbox_OT_VgroupsSelectVertices.bl_idname)
        row.operator(SimpleToolbox_OT_VgroupsDeselectVertices.bl_idname)

        row = layout.row()
        row.prop(bpy.context.scene.tool_settings, "vertex_group_weight")

        # Separator
        row = layout.row()
        row.separator(factor=1.0)

    # Remove Selected Vgroups
    row = layout.row(align=True)
    row.operator(SimpleToolbox_OT_VgroupsRemoveSelected.bl_idname)
    row.operator(SimpleToolbox_OT_VgroupsKeepSelected.bl_idname)

    row = layout.row(align=True)
    row.operator(SimpleToolbox_OT_VgroupsSelectObjectsWithVgroups.bl_idname)

    # MESH_MT_vertex_group_context_menu
