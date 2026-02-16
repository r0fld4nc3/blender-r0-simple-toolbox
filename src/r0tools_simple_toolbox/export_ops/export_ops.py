import logging

import bpy

from .. import utils as u

log = logging.getLogger(__name__)


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
    if not u.is_writing_context_safe(bpy.context.scene):
        log.warning(f"Export Ops Remove Export Set At Index: Unsafe Context.")
        return None

    export_sets = get_export_sets()

    if index < get_export_sets_count():
        export_sets.remove(index)


def set_active_export_set_index(index: int):
    if not u.is_writing_context_safe(bpy.context.scene):
        log.warning(f"Export Ops Set Active Export Set Index: Unsafe Context.")
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
    if not u.is_writing_context_safe(bpy.context.scene):
        log.warning(f"Export Ops Set Export Set Name: Unsafe Context.")
        return None

    try:
        export_set.name = new_name
    except Exception as e:
        log.warning(f"[ERROR] Unable to rename object set: {e}")
        return False

    return True


def set_export_set_name_at_index(index, new_name) -> bool:
    if not u.is_writing_context_safe(bpy.context.scene):
        log.warning(f"Export Ops Set Export Set Name At Index: Unsafe Context.")
        return None

    export_set = get_export_set_at_index(index)

    if export_set:
        export_set.name = new_name
        return True

    return False


def draw_quick_export_sets_uilist(layout, context):
    """Draw the Quick Export Sets UI list"""

    from .operators import (
        SimpleToolbox_OT_AddExportSet,
        SimpleToolbox_OT_BatchExportObjects,
        SimpleToolbox_OT_RemoveExportSet,
        SimpleToolbox_OT_SelectPath,
    )

    if not u.is_writing_context_safe(bpy.context.scene):
        log.warning(f"Export Sets Draw UIList: Unsafe Context.")
        return None

    path_row_height_scale = 1.2

    addon_prefs = u.get_addon_prefs()
    addon_export_props = u.get_addon_export_props()
    addon_object_sets_props = u.get_addon_object_sets_props()

    # Global Settings Button
    global_settings_btn_row = layout.row()
    global_settings_btn_row.prop(
        addon_export_props,
        "show_edit_global_fbx_export_settings",
        text="Global Settings",
        icon="PREFERENCES",
    )
    global_settings_btn_row.scale_y = path_row_height_scale

    if addon_export_props.show_edit_global_fbx_export_settings:
        draw_fbx_export_settings(layout, addon_prefs.export_settings_global_fbx)

    # Export Sets Row Number Slider
    row = layout.row()
    col_left = row.column()
    col_left.alignment = "LEFT"
    col_left.prop(addon_export_props, "export_sets_list_rows", text="Rows:")
    col_right = row.column()
    col_right.separator()

    row = layout.row()

    # Left Section - List
    col_left = row.column()

    col_left.template_list(
        "R0PROP_UL_ExportSetsList",
        "",
        addon_export_props,
        "export_sets",
        addon_export_props,
        "active_index",
        rows=addon_export_props.export_sets_list_rows,
    )

    batch_export_row = col_left.row()
    batch_export_row.operator(SimpleToolbox_OT_BatchExportObjects.bl_idname, icon="EXPORT")

    # Right side - Buttons
    col_right = row.column(align=True)
    col_right.alignment = "RIGHT"
    col_right.scale_x = addon_prefs.OPERATOR_COLUMN_SIZE_X
    col_right.operator(SimpleToolbox_OT_AddExportSet.bl_idname, text="+")
    col_right.operator(SimpleToolbox_OT_RemoveExportSet.bl_idname, text="-")

    # Selected Export Set Options
    active_index = get_active_export_set_index()
    export_item = get_export_set_at_index(active_index)

    if not export_item:
        return

    path_row = layout.row(align=True)
    path_row.prop(export_item, "export_path", text="")
    op = path_row.operator(SimpleToolbox_OT_SelectPath.bl_idname, text="", icon="FILE_FOLDER")
    op.index = active_index

    # Use Object Sets button
    path_row.prop(
        export_item,
        "use_object_sets",
        text="",
        icon="MESH_CUBE" if export_item.use_object_sets else "RESTRICT_SELECT_OFF",
    )

    options_panel_header, options_panel = layout.panel("simpletoolbox_pt_export_options", default_closed=True)
    if options_panel_header:
        options_panel_header.label(text="Options")

    if options_panel:
        # Frame Export Settings
        frame_export_header, frame_export_panel = options_panel.panel(
            "simpletoolbox_pt_frame_export", default_closed=True
        )
        if frame_export_header:
            frame_export_header.label(text="Export frame")

        if frame_export_panel:
            export_row = frame_export_panel.row()
            export_row.alignment = "RIGHT"

            # Checkbox
            export_row.prop(export_item, "export_at_frame", text="")

            # Frame Column
            right_col = export_row.column()
            right_col.scale_x = 0.88
            right_col.enabled = export_item.export_at_frame  # Dynamic contextual enable
            right_col.prop(export_item, "export_frame")

        # FBX Export Settings
        custom_fbx_settings_header, custom_fbx_settings_panel = options_panel.panel(
            "simpletoolbox_pt_export_fbx_settings", default_closed=True
        )
        if custom_fbx_settings_header:
            custom_fbx_settings_header.label(text="FBX Settings Override")

        if custom_fbx_settings_panel:
            checkbox_row = custom_fbx_settings_panel.row()
            checkbox_row.alignment = "RIGHT"
            checkbox_row.prop(export_item, "use_custom_fbx_settings")
            if export_item.use_custom_fbx_settings:
                settings_row = custom_fbx_settings_panel.row()
                draw_fbx_export_settings(settings_row, export_item.export_settings_fbx)

        # Object Sets Row
        if export_item.use_object_sets:
            object_sets_panel_header, object_sets_panel = options_panel.panel(
                "simpletoolbox_pt_export_use_object_sets", default_closed=True
            )

            if object_sets_panel_header:
                object_sets_panel_header.label(text="Object Sets")

            if object_sets_panel:
                available_sets = u.get_object_sets()

                if available_sets:
                    object_sets_panel.template_list(
                        "R0PROP_UL_ObjectSetsViewList",
                        "",
                        addon_object_sets_props,
                        "object_sets",
                        addon_object_sets_props,
                        "object_sets_index",
                        rows=len([obj_set for obj_set in available_sets if not obj_set.separator]),
                    )
                else:
                    no_sets_row = object_sets_panel.row()
                    no_sets_row.label(text="No Object Sets available", icon="INFO")


def draw_fbx_export_settings(layout, settings):
    """Draw FBX export settings UI"""

    split_factor = 0.5

    main_col = layout.column()

    # Include
    box = main_col.box()
    box.label(text="Include")

    row = box.row()
    col = row.column()

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Limit to")
    prop_row.prop(settings, "use_selection")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_visible")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_active_collection")
    if settings.use_active_collection:
        prop_row.prop(settings, "collection", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Object Types:")
    prop_col = prop_row.column(align=True)
    for export_type in (
        ("export_empty", "Empty"),
        ("export_camera", "Camera"),
        ("export_light", "Light"),
        ("export_armature", "Armature"),
        ("export_mesh", "Mesh"),
        ("export_other", "Other"),
    ):
        prop_col.prop(settings, export_type[0], text=export_type[1], toggle=True)

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_custom_props")

    # Transform
    box = main_col.box()
    box.label(text="Transform", icon="ORIENTATION_GLOBAL")

    row = box.row(align=True)
    col = row.column()

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Scale")
    prop_row.prop(settings, "global_scale", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Apply Scalings")
    prop_row.prop(settings, "apply_scale_options", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Forward")
    prop_row.prop(settings, "axis_forward", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Up")
    prop_row.prop(settings, "axis_up", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "apply_unit_scale")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_space_transform")
    # row.prop(settings, "bake_space_transform")

    # Geometry
    box = main_col.box()
    box.label(text="Geometry", icon="MESH_DATA")

    row = box.row()
    col = row.column()

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Smoothing")
    prop_row.prop(settings, "mesh_smooth_type", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_subsurf")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_mesh_modifiers")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_mesh_edges")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_triangles")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_tspace")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Vertex Colours")
    prop_row.prop(settings, "colors_type", text="")
    if settings.colors_type != "NONE":
        prop_row = col.row()
        prop_row.label(text="")  # Spacer
        prop_row.prop(settings, "prioritize_active_color")

    # Armature
    box = main_col.box()
    box.label(text="Armature", icon="ARMATURE_DATA")

    row = box.row()
    col = row.column()

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Primary Bone Axis")
    prop_row.prop(settings, "primary_bone_axis", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Secondary Bone Axis")
    prop_row.prop(settings, "secondary_bone_axis", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Armature Type")
    prop_row.prop(settings, "armature_nodetype", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "use_armature_deform_only")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="")  # Spacer
    prop_row.prop(settings, "add_leaf_bones")

    # Animation
    box = main_col.box()
    # box.label(text="Animation", icon="ANIM")
    row = box.row()
    row.prop(settings, "bake_anim", text="")
    row.label(text="Animation", icon="ANIM")

    row = box.row()
    col = row.column()

    if settings.bake_anim:
        prop_row = col.split(factor=split_factor)
        prop_row.alignment = "RIGHT"
        prop_row.label(text="")  # Spacer
        prop_row.prop(settings, "bake_anim_use_all_bones")

        prop_row = col.split(factor=split_factor)
        prop_row.alignment = "RIGHT"
        prop_row.label(text="")  # Spacer
        prop_row.prop(settings, "bake_anim_use_nla_strips")

        prop_row = col.split(factor=split_factor)
        prop_row.alignment = "RIGHT"
        prop_row.label(text="")  # Spacer
        prop_row.prop(settings, "bake_anim_use_all_actions")

        prop_row = col.split(factor=split_factor)
        prop_row.alignment = "RIGHT"
        prop_row.label(text="")  # Spacer
        prop_row.prop(settings, "bake_anim_force_startend_keying")

        prop_row = col.split(factor=split_factor)
        prop_row.alignment = "RIGHT"
        prop_row.label(text="")  # Spacer
        prop_row.prop(settings, "bake_anim_step")

        prop_row = col.split(factor=split_factor)
        prop_row.alignment = "RIGHT"
        prop_row.label(text="")  # Spacer
        prop_row.prop(settings, "bake_anim_simplify_factor")

    # File Settings
    box = main_col.box()
    box.label(text="File", icon="FILE")

    row = box.row()
    col = row.column()

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Path Mode")
    prop_row.prop(settings, "path_mode", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Embed Textures")
    prop_row.prop(settings, "embed_textures", text="")

    prop_row = col.split(factor=split_factor)
    prop_row.alignment = "RIGHT"
    prop_row.label(text="Use Metadata")
    prop_row.prop(settings, "use_metadata", text="")
