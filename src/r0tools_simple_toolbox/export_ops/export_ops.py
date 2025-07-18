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

    # Global Settings Section
    global_settings_row = layout.row()
    global_settings_row.prop(
        addon_export_props,
        "show_edit_global_fbx_export_settings",
        text="",
        icon="PREFERENCES",
    )

    if addon_export_props.show_edit_global_fbx_export_settings:
        draw_fbx_export_settings(global_settings_row, addon_prefs.export_settings_global_fbx, is_global=True)

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


def draw_quick_export_sets_entries(layout, context):
    from .operators import (
        SimpleToolbox_OT_AddExportSet,
        SimpleToolbox_OT_ExportObjects,
        SimpleToolbox_OT_RemoveExportSet,
        SimpleToolbox_OT_SelectPath,
        SimpleToolbox_OT_ToggleObjectSetSelection,
    )

    if not u.is_writing_context_safe(bpy.context.scene, check_addon_props=True):
        print(f"[WARNING] [{_mod}] Export Sets Draw UIList: Unsafe Context.")
        return None

    addon_prefs = u.get_addon_prefs()
    addon_export_props = u.get_addon_export_props()

    button_row_scale_x_factor = 0.15
    button_row_scale_y_factor = 1.2
    path_row_height_scale = 1.2
    export_button_width_scale = 1.5
    item_spacing_factor = 1.5

    export_sets = get_export_sets()

    # Global Settings Section
    global_settings_row = layout.row()
    global_settings_row.prop(
        addon_export_props,
        "show_edit_global_fbx_export_settings",
        text="",
        icon="PREFERENCES",
    )

    if addon_export_props.show_edit_global_fbx_export_settings:
        draw_fbx_export_settings(global_settings_row, addon_prefs.export_settings_global_fbx, is_global=True)

    # Separator between global settings and export entries
    layout.separator(factor=2.0)

    # Create main row
    main_row = layout.row(align=False)

    # Left column for entries
    left_col = main_row.column(align=True)

    # Right column for buttons
    right_col = main_row.column(align=True)
    right_col.scale_x = button_row_scale_x_factor
    right_col.scale_y = button_row_scale_y_factor

    # Add
    button_col = right_col.column(align=True)
    button_col.operator(SimpleToolbox_OT_AddExportSet.bl_idname, text="+")

    for index, export_item in enumerate(export_sets):
        # Left Col
        entry_box = left_col.box()
        header_row = entry_box.row()

        if export_item.export_set_name:
            header_row.prop(export_item, "export_set_name", text="", emboss=True)
        else:
            # Show placeholder text when name is empty
            header_row.prop(
                export_item,
                "export_set_name",
                text="",
                emboss=True,
                placeholder=f"Export Set {index + 1}",
            )

        # Settings toggle button
        header_row.prop(export_item, "use_custom_settings", text="", icon="PREFERENCES")

        remove_export_set_op = header_row.operator(
            SimpleToolbox_OT_RemoveExportSet.bl_idname, emboss=False, text="", icon="X"
        )
        remove_export_set_op.index = index

        ################
        ### PATH ROW ###
        ################

        path_row = entry_box.row(align=True)
        path_row.scale_y = path_row_height_scale

        path_content = path_row.row(align=True)

        # Export button (in a sub-row) so we can have red button
        export_sub_row = path_content.row(align=True)
        export_sub_row.scale_x = export_button_width_scale
        export_sub_row.alert = True

        export_op = export_sub_row.operator(SimpleToolbox_OT_ExportObjects.bl_idname, text="", icon="EXPORT")
        export_op.export_path = export_item.export_path
        export_op.mkdirs_if_not_exist = addon_export_props.mkdirs_if_not_exist

        if export_item.use_object_sets:
            selected_object_sets = export_item.get_selected_object_sets()
            export_op.object_set_names = ", ".join(selected_object_sets)
        else:
            export_op.object_set_names = ""

        # Path and Select
        path_content.prop(export_item, "export_path", text="")
        op = path_content.operator(SimpleToolbox_OT_SelectPath.bl_idname, text="", icon="FILE_FOLDER")
        op.index = index

        # Use Object Sets button
        path_content.prop(
            export_item,
            "use_object_sets",
            text="",
            icon="MESH_CUBE" if export_item.use_object_sets else "RESTRICT_SELECT_OFF",
        )

        # Object Sets Row
        if export_item.use_object_sets:
            available_sets = u.get_object_sets()

            if available_sets:
                selected_names = {obj_set.name for obj_set in export_item.object_sets_names if obj_set.is_selected}

                object_sets_row = entry_box.row()
                object_sets_row.alignment = "LEFT"

                object_sets_row.prop(
                    export_item,
                    "object_sets_expanded",
                    text="Choose Object Sets",
                    icon="TRIA_DOWN" if export_item.object_sets_expanded else "TRIA_RIGHT",
                    emboss=False,
                )

                if export_item.object_sets_expanded:
                    # Box for object sets
                    box_row = entry_box.row()
                    object_sets_box = box_row.box()
                    object_sets_col = object_sets_box.column(align=True)

                    # Draw each available object set
                    for obj_set in available_sets:
                        if obj_set.separator:
                            continue

                        set_row = object_sets_col.row(align=True)

                        # Check if this set is in our collection and selected
                        is_selected = obj_set.name in selected_names
                        icon = "CHECKBOX_HLT" if is_selected else "CHECKBOX_DEHLT"

                        # Toggle selection with purpose-built Operator
                        op = set_row.operator(
                            SimpleToolbox_OT_ToggleObjectSetSelection.bl_idname, text="", icon=icon, emboss=False
                        )
                        op.export_set_index = index
                        op.object_set_name = obj_set.name

                        set_row.separator(factor=1.0)

                        set_row.label(text=obj_set.name)
            else:
                no_sets_row = entry_box.row()
                no_sets_row.label(text="No Object Sets available", icon="INFO")

        # Button state based on context selection
        if export_item.use_object_sets:
            selected_sets = export_item.get_selected_object_sets()
            export_sub_row.enabled = bool(selected_sets) and bool(export_item.export_path)
        else:
            export_sub_row.enabled = len(u.get_selected_objects()) > 0 and bool(export_item.export_path)

        # Items spacing
        left_col.row()
        left_col.separator(factor=item_spacing_factor)


def draw_fbx_export_settings(layout, settings, is_global=False):
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
    prop_row.prop(settings, "vertex_colours_type", text="")
    if settings.vertex_colours_type != "NONE":
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
