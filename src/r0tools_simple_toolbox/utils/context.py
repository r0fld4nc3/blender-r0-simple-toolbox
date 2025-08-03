from pathlib import Path

import bpy

from ..defines import INTERNAL_NAME, TOOLBOX_PROPS_NAME
from .boxcutter import boxcutter_running

_mod = "UTILS.CONTEXT"


def get_addon_props():
    """Get the addon property group from current scene"""
    return get_scene().r0fl_toolbox_props


def get_addon_object_sets_props():
    """Get the addon property group from current scene"""
    return get_scene().r0fl_object_sets_props


def get_addon_vertex_groups_props():
    """Get the addon property group from current scene"""
    return get_scene().r0fl_vertex_groups_props


def get_addon_edge_data_props():
    """Get the addon property group from current scene"""
    return get_scene().r0fl_toolbox_edge_data_props


def get_addon_experimental_props():
    """Get the addon property group from current scene"""
    return get_scene().r0fl_toolbox_experimental_props


def get_addon_find_modifier_props():
    """Get the addon property group from current scene"""
    return get_scene().r0fl_toolbox_find_modifier_props


def get_addon_export_props():
    """Get the addon property group from current scene"""
    return get_scene().r0fl_toolbox_export_props


def get_addon_prefs():
    """Get the addon preferences"""
    return bpy.context.preferences.addons[INTERNAL_NAME].preferences


def get_scene() -> bpy.types.Scene:
    """Get the current scene"""
    return bpy.context.scene


def get_scene_name() -> str:
    """Get the name of the current scene"""
    return get_scene().name


def get_selection_mode(as_str=False) -> int | str:
    select_mode = bpy.context.tool_settings.mesh_select_mode

    mode_str = "VERT" if select_mode[0] else "EDGE" if select_mode[1] else "FACE" if select_mode[2] else "NONE"
    mode_int = 0 if select_mode[0] else 1 if select_mode[1] else 2 if select_mode[2] else -1

    if as_str:
        return mode_str

    return mode_int


def get_context_area() -> str | None:
    """Get the current area type or None if unavailable"""
    if not bpy.context.area:
        return None
    return bpy.context.area.ui_type


def get_addon_fs_path() -> Path:
    """Get the filesystem path to the addon directory from THIS file"""
    return Path(__file__).resolve().parent.parent


def get_depsgraph():
    """Get the current dependency graph"""
    return bpy.context.evaluated_depsgraph_get()


def get_depsgraph_is_updated_geometry() -> bool:
    """Check if geometry was updated in the depsgraph"""
    d = get_depsgraph()
    for update in d.updates:
        return update.is_updated_geometry
    return False


def get_depsgraph_is_updated_shading() -> bool:
    """Check if shading was updated in the depsgraph"""
    d = get_depsgraph()
    for update in d.updates:
        return update.is_updated_shading
    return False


def get_depsgraph_is_updated_transform() -> bool:
    """Check if transforms were updated in the depsgraph"""
    d = get_depsgraph()
    for update in d.updates:
        return update.is_updated_transform
    return False


def is_viewport_local() -> bool:
    area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
    space = area.spaces.active
    if space.local_view:
        return True

    return False


def toggle_viewport_local_mode():
    area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
    with bpy.context.temp_override(area=area):
        bpy.ops.view3d.localview(frame_selected=False)


def get_uvmap_size_x():
    """Get selected UV Map Size in X"""
    addon_props = get_addon_props()
    return int(addon_props.uv_size_x)


def get_uvmap_size_y():
    """Get selected UV Map Size in Y"""
    addon_props = get_addon_props()
    return int(addon_props.uv_size_y)


def is_writing_context_safe(scene) -> bool:
    """
    Potential fix for "AttributeError: Writing to ID classes in this context is now allowed: Scene, Scene datablock
    """

    from .general import LOG

    addon_prefs = get_addon_prefs()

    if not hasattr(scene, TOOLBOX_PROPS_NAME):
        if addon_prefs is not None and hasattr(addon_prefs, "lock_states_avoided"):
            addon_prefs.lock_states_avoided += 1
            LOG(f"[INFO] [{_mod}] Scene does not have proper attribute(s). Skipping.")
        return False

    # Check for boxcutter running
    if boxcutter_running():
        LOG(f"[MONITOR] [{_mod}] Boxcutting running. Skipping.")
        return False

    # Check if rendering or baking is active
    if scene.render.use_lock_interface:
        LOG(f"[MONITOR] [{_mod}] Interface is locked (rendering/baking). Skipping.")
        return False

    # Check for active jobs
    jobs = ("RENDER", "COMPOSITE", "OBJECT_BAKE")
    jobs_active = [bpy.app.is_job_running(job) for job in jobs]
    if any(jobs_active):
        LOG(f"[MONITOR] [{_mod}] Active job(s) detected. Skipping.")
        return False

    # Additional check for bake operator
    if hasattr(bpy.context, "active_operator") and bpy.context.active_operator:
        op_idname = bpy.context.active_operator.bl_idname
        if "bake" in op_idname.lower():
            LOG(f"[MONITOR] [{_mod}] Bake operator active: {op_idname}. Skipping.")
            return False

    return True


def save_preferences():
    """Safely save user preferences without causing recursion"""
    try:
        if not hasattr(save_preferences, "is_saving"):
            save_preferences.is_saving = False

        if not save_preferences.is_saving:
            save_preferences.is_saving = True
            bpy.context.preferences.use_preferences_save = True
            bpy.ops.wm.save_userpref()
            save_preferences.is_saving = False
    except Exception as e:
        print(f"[ERROR] [{_mod}] Error saving preferences: {e}")
        save_preferences.is_saving = False
