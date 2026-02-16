import logging
from pathlib import Path

import bpy

from ..defines import INTERNAL_NAME, TOOLBOX_PROPS_NAME

log = logging.getLogger(__name__)


def get_active_modal_operators(context: bpy.types.Context = None) -> list:
    """
    Return a `list` of active Modal Operators.

    When no Modal Operators are running, it will return an empty list
    """

    if context is None:
        context = bpy.context

    if not hasattr(context, "window"):
        return []

    if not hasattr(context.window, "modal_operators"):
        return []

    return context.window.modal_operators if context else []


def get_addon_props(scene=None):
    """Get the addon property group from current scene"""
    return get_scene(scene).r0fl_toolbox_props


def get_addon_object_sets_props(scene=None):
    """Get the addon property group from current scene"""
    return get_scene(scene).r0fl_object_sets_props


def get_object_props(obj: bpy.types.Object):
    """Get the Object-level Object properties from the given Object"""
    return obj.r0fl_toolbox_props


def get_addon_vertex_groups_props(scene=None):
    """Get the addon property group from current scene"""
    return get_scene(scene).r0fl_vertex_groups_props


def get_addon_edge_data_props(scene=None):
    """Get the addon property group from current scene"""
    return get_scene(scene).r0fl_toolbox_edge_data_props


def get_addon_experimental_props(scene=None):
    """Get the addon property group from current scene"""
    return get_scene(scene).r0fl_toolbox_experimental_props


def get_addon_find_modifier_props(scene=None):
    """Get the addon property group from current scene"""
    return get_scene(scene).r0fl_toolbox_find_modifier_props


def get_addon_export_props(scene=None):
    """Get the addon property group from current scene"""
    return get_scene(scene).r0fl_toolbox_export_props


def get_addon_prefs():
    """Get the addon preferences"""
    return bpy.context.preferences.addons[INTERNAL_NAME].preferences


def get_scene(scene=None) -> bpy.types.Scene:
    """Get the current scene"""
    return scene if scene else bpy.context.scene


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


def is_saving() -> bool:
    from .. import depsgraph

    return depsgraph.is_saving


def is_updating() -> bool:
    from .. import depsgraph

    return depsgraph.is_updating


def set_is_updating(state: bool):
    from .. import depsgraph

    depsgraph.is_updating = state


def is_writing_context_safe(scene) -> bool:
    """
    Potential fix for "AttributeError: Writing to ID classes in this context is now allowed: Scene, Scene datablock
    """

    from .general import log

    if is_saving():
        log.info(f"Unsafe write context while file is being saved.")
        return False

    scene = get_scene(scene)

    if not hasattr(scene, TOOLBOX_PROPS_NAME):
        log.info(f"Scene does not have proper attribute(s) '{TOOLBOX_PROPS_NAME}'. Skipping.")
        return False

    # Check if rendering or baking is active
    if scene.render.use_lock_interface:
        log.info(f"[MONITOR] Interface is locked (rendering/baking). Skipping.")
        return False

    """
    # Check for active jobs
    jobs = ("RENDER", "COMPOSITE", "OBJECT_BAKE")
    jobs_active = [bpy.app.is_job_running(job) for job in jobs]
    if any(jobs_active):
        log.info(f"[MONITOR] Active job(s) detected. Skipping.")
        return False
    """

    # Additional check for bake operator
    if hasattr(bpy.context, "active_operator") and bpy.context.active_operator:
        op_idname = bpy.context.active_operator.bl_idname
        if "bake" in op_idname.lower():
            log.info(f"[MONITOR] Bake operator active: {op_idname}. Skipping.")
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
        log.error(f"Error saving preferences: {e}")
        save_preferences.is_saving = False
