import bpy

from .. import utils as u

_mod = "EXPORT_SETS"


def get_export_sets() -> list:
    addon_export_sets_props = u.get_addon_export_props()

    return addon_export_sets_props.export_sets


def get_export_sets_count() -> int:
    return len(get_export_sets())


def get_active_export_set_index() -> int:
    addon_export_set_props = u.get_addon_export_props()
    active_index = addon_export_set_props.active_index

    return active_index


def get_export_set_at_index(index: int):
    export_sets = get_export_sets()

    if index < get_export_sets_count():
        return export_sets[index]

    return None


def remove_export_set_at_index(index: int):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Export Ops Remove Export Set At Index: Unsafe Context.")
        return None

    export_sets = get_export_sets()

    if index < get_export_sets_count():
        export_sets.remove(index)


def set_active_export_set_index(index: int):
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Export Ops Set Active Export Set Index: Unsafe Context.")
        return None

    addon_export_sets_props = u.get_addon_export_props()

    if index < get_export_sets_count():
        addon_export_sets_props.active_index = index


def get_export_set_name_at_index(index: int) -> str:
    export_set = get_export_set_at_index(index)

    if not export_set:
        return ""

    return export_set.name


def set_export_set_name(export_set, new_name) -> bool:
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Export Ops Set Export Set Name: Unsafe Context.")
        return None

    try:
        export_set.name = new_name
    except Exception as e:
        print(f"[ERROR] [{_mod}] Unable to rename object set: {e}")
        return False

    return True


def set_export_set_name_at_index(index, new_name) -> bool:
    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Export Ops Set Export Set Name At Index: Unsafe Context.")
        return None

    export_set = get_export_set_at_index(index)

    if export_set:
        export_set.name = new_name
        return True

    return False


def draw_quick_export_sets_uilist(layout, context):
    """
    Draw the Quick Export Sets UI list

    Args:
        layout: The layout to draw in
        context: The current context
    """

    from .operators import (
        SimpleToolbox_OT_AddExportSet,
        SimpleToolbox_OT_RemoveExportSet,
    )

    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Export Sets Draw UIList: Unsafe Context.")
        return None

    addon_prefs = u.get_addon_prefs()
    addon_export_props = u.get_addon_export_props()

    # Export Sets Row Number Slider
    row = layout.row()
    split = row.split(factor=0.35)
    col = split.column()
    col.prop(addon_prefs, "export_sets_list_rows", text="Rows:")
    col = split.column()
    col.separator()

    row = layout.row()
    split = row.split(factor=0.92)  # Affects right side button width

    # Left Section - List
    col = split.column()

    # Draw the UIList
    col.template_list(
        "R0PROP_UL_ExportSetsList",
        "",
        addon_export_props,
        "export_sets",
        addon_export_props,
        "active_index",
        rows=addon_prefs.export_sets_list_rows,
    )

    # Right side - Buttons
    col = split.column(align=True)
    col.operator(SimpleToolbox_OT_AddExportSet.bl_idname, text="+")
    col.operator(SimpleToolbox_OT_RemoveExportSet.bl_idname, text="-")
