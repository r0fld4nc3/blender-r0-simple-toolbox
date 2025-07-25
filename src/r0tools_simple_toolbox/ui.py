import bpy

from . import ext_update as upd
from . import utils as u
from .defines import ADDON_CATEGORY, ADDON_NAME_BARE, DEBUG, IDNAME_EXTRA, VERSION_STR
from .operators import *
from .repo import draw_repo_layout

_mod = "UI"


class r0Tools_PT_SimpleToolbox(bpy.types.Panel):
    bl_idname = "OBJECT_PT_simple_toolbox"
    bl_label = f"{ADDON_NAME_BARE}.{IDNAME_EXTRA} ({VERSION_STR})"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_CATEGORY
    # bl_options = {"DEFAULT_CLOSED"}
    has_update = False

    @classmethod
    def _update_callback(cls, result):
        cls.has_update = result

        # Trigger redraw
        try:
            for area in bpy.context.screen.areas:
                if area.type == cls.bl_space_type:
                    area.tag_redraw()
        except Exception as e:
            print(f"[ERROR] [{_mod}] Failed to redraw on callback:\n{e}")

    def draw(self, context):
        addon_props = u.get_addon_props()
        addon_prefs = u.get_addon_prefs()
        addon_find_modifier_props = u.get_addon_find_modifier_props()

        layout = self.layout

        categories_row = layout.row()
        categories_row.prop(addon_props, "cat_show_object_ops", text="", icon="EVENT_O")
        categories_row.prop(addon_props, "cat_show_mesh_ops", text="", icon="EVENT_M")
        categories_row.prop(addon_props, "cat_show_uv_ops", text="", icon="EVENT_U")
        categories_row.prop(addon_props, "cat_show_custom_properties_editor", text="", icon="EVENT_C")
        categories_row.prop(addon_props, "cat_show_find_modifiers_ops", text="", icon="MODIFIER")
        categories_row.prop(addon_props, "cat_show_object_sets_editor", text="", icon="MESH_CUBE")
        categories_row.prop(addon_props, "cat_show_vertex_groups_editor", text="", icon="GROUP_VERTEX")
        categories_row.separator(factor=1.0)
        categories_row.prop(addon_prefs, "dev_tools", text="", icon="TOOL_SETTINGS")
        categories_row.prop(addon_prefs, "experimental_features", text="", icon="EXPERIMENTAL")

        cat_show_object_ops = addon_props.cat_show_object_ops
        cat_show_mesh_ops = addon_props.cat_show_mesh_ops
        cat_show_uv_ops = addon_props.cat_show_uv_ops
        cat_show_find_modifiers_ops = addon_props.cat_show_find_modifiers_ops
        cat_show_object_sets_editor = addon_props.cat_show_object_sets_editor
        cat_show_vertex_groups_editor = addon_props.cat_show_vertex_groups_editor
        cat_show_custom_properties_editor = addon_props.cat_show_custom_properties_editor

        if self.has_update:
            from .repo import SimpleToolbox_OT_TakeMeToUpdate

            update_box = layout.box()
            update_row = update_box.row(align=True)
            update_row.label(text="", icon="FUND")
            update_row.label(text="UPDATE AVAILABLE", icon="FILE_REFRESH")
            update_row.label(text="", icon="FUND")
            update_row = update_box.row(align=True)
            update_row.operator(
                SimpleToolbox_OT_TakeMeToUpdate.bl_idname, text="Take me there!", icon="INDIRECT_ONLY_ON"
            )

        # ====== Dev Tools ======
        if addon_prefs.dev_tools:
            dev_tools_box = layout.box()
            dev_tools_box.prop(
                addon_props,
                "show_dev_tools",
                icon="TRIA_DOWN" if addon_props.show_dev_tools else "TRIA_RIGHT",
                emboss=False,
            )
            if addon_props.show_dev_tools:
                row = dev_tools_box.row()
                row.prop(addon_prefs, "debug", text="Debug", icon="EXPERIMENTAL")
                row.prop(addon_prefs, "log_output", text="Log", icon="CONSOLE")
                row = dev_tools_box.row()
                row.operator(BUILTINS_OT_IconViewer.bl_idname)
                row = dev_tools_box.row()
                row.operator("script.reload", text="Reload All Scripts", icon="PACKAGE")
                reload_user_defined_box = dev_tools_box.box()
                row = reload_user_defined_box.row()
                row.prop(addon_props, "reload_modules_prop")
                row = reload_user_defined_box.row()
                row.operator(SimpleToolbox_OT_ReloadNamedScripts.bl_idname, icon="TOOL_SETTINGS")

                if addon_prefs.experimental_features:
                    row = dev_tools_box.row()
                    row.operator("image.reload", icon="IMAGE_DATA")
                    row = dev_tools_box.row()
                    row.operator(SimpleToolbox_OT_FixImageDataPaths.bl_idname, icon="IMAGE_DATA")

        # ====== Object Ops ======
        if cat_show_object_ops:
            object_ops_header, object_ops_panel = layout.panel("simpletoolbox_pt_object_ops", default_closed=True)
            if object_ops_header:
                object_ops_header.label(text="Object Ops")

            if object_ops_panel:
                # >> Row
                object_ops_panel_row = object_ops_panel.row(align=True)
                row_split = object_ops_panel_row.split(align=True)
                # Clear Split Normals Data
                row_split.operator(SimpleToolbox_OT_ClearCustomSplitNormalsData.bl_idname)
                # Clear Objects Children
                row_split.operator(SimpleToolbox_OT_ClearChildrenRecurse.bl_idname)

                # >> Row
                object_ops_panel_row = object_ops_panel.row(align=True)
                row_split = object_ops_panel_row.split(align=True)
                # Select Empty Objects
                row_split.operator(SimpleToolbox_OT_SelectEmptyObjects.bl_idname)

                # >> Row
                object_ops_panel_row = object_ops_panel.row(align=True)
                row_split = object_ops_panel_row.split(align=True)
                # Remove unused Materials
                row_split.operator(SimpleToolbox_OT_RemoveUnusedMaterials.bl_idname)

        # ====== Mesh Ops ======
        if cat_show_mesh_ops:
            mesh_ops_header, mesh_ops_panel = layout.panel("simpletoolbox_pt_mesh_ops", default_closed=True)
            if mesh_ops_header:
                mesh_ops_header.label(text="Mesh Ops")

            if mesh_ops_panel:
                # >> Row
                mesh_ops_panel_row = mesh_ops_panel.row(align=True)
                row_split = mesh_ops_panel_row.split(align=True)
                # Remove Nth Edges Operator
                row_split.operator(SimpleToolbox_OT_DissolveNthEdge.bl_idname)
                if addon_prefs.experimental_features:
                    row_split.operator(SimpleToolbox_OT_RestoreNthEdge.bl_idname)

                # >> Row
                mesh_ops_panel_row = mesh_ops_panel.row(align=True)
                mesh_ops_panel_row.operator(SimpleToolbox_OT_ResetEdgeData.bl_idname)

                # >> Row
                mesh_ops_panel_row = mesh_ops_panel.row(align=True)
                row_split = mesh_ops_panel_row.split(align=True)
                # Restore rotation from Selection
                row_split.operator(SimpleToolbox_OT_RestoreRotationFromSelection.bl_idname)

                """
                # Clear Sharp Edges on Axis
                clear_sharp_edges_box = mesh_ops_panel.box()
                row = clear_sharp_edges_box.row(align=True)
                clear_sharp_edges_box.prop(
                    addon_props,
                    "show_clear_sharps_on_axis",
                    icon="TRIA_DOWN" if addon_props.show_clear_sharps_on_axis else "TRIA_RIGHT",
                    emboss=False,
                )
                if addon_props.show_clear_sharps_on_axis:
                    row = clear_sharp_edges_box.row(align=True)
                    row.prop(addon_prefs, "clear_sharp_axis_float_prop", text="Threshold")
                    row = clear_sharp_edges_box.row(align=True)
                    row.scale_x = 5
                    row.operator(SimpleToolbox_OT_ClearAxisSharpEdgesX.bl_idname, text="X")
                    row.operator(SimpleToolbox_OT_ClearAxisSharpEdgesY.bl_idname, text="Y")
                    row.operator(SimpleToolbox_OT_ClearAxisSharpEdgesZ.bl_idname, text="Z")
                """

        # ====== Custom Properties UI List ======
        if cat_show_custom_properties_editor:
            custom_properties_header, custom_properties_panel = layout.panel(
                "simpletoolbox_pt_custom_properties", default_closed=True
            )
            if custom_properties_header:
                custom_properties_header.label(text="Custom Properties")

            if custom_properties_panel:
                custom_properties_panel_row = custom_properties_panel.row()
                # Row Number Slider
                row = custom_properties_panel_row.row()
                split = row.split(factor=0.35)
                split.prop(addon_prefs, "custom_properties_list_rows", text="Rows:")

                row = custom_properties_panel.row()
                row.template_list(
                    "R0PROP_UL_CustomPropertiesList",
                    "custom_property_list",
                    u.get_addon_props(),  # Collection owner
                    "custom_property_list",  # Collection property
                    u.get_addon_props(),  # Active item owner
                    "custom_property_list_index",  # Active item property
                    rows=addon_prefs.custom_properties_list_rows,
                )
                # Clear Custom Properties
                row = custom_properties_panel.row()
                row.operator(SimpleToolbox_OT_ClearCustomProperties.bl_idname)

        # ====== UV Ops ======
        if cat_show_uv_ops:
            uv_ops_header, uv_ops_panel = layout.panel("simpletoolbox_pt_uv_ops", default_closed=True)
            if uv_ops_header:
                uv_ops_header.label(text="UV Ops")

            if uv_ops_panel:
                uv_ops_panel_row = uv_ops_panel.row()

                # UV Map Target Resolution
                row = uv_ops_panel_row.row()
                row.label(text="UV Map")

                dropdown_col = uv_ops_panel_row.column(align=True)
                dropdown_col.prop(addon_props, "uv_size_x", text="Width")
                dropdown_col.prop(addon_props, "uv_size_y", text="Height")

                # UV Island Thresholds
                uv_island_thresholds_header, uv_island_thresholds_panel = uv_ops_panel.panel(
                    "simpletoolbox_pt_uv_island_thresholds", default_closed=True
                )
                if uv_island_thresholds_header:
                    uv_island_thresholds_header.label(text="UV Island Area Thresholds")

                if uv_island_thresholds_panel:
                    values_row = uv_island_thresholds_panel.row()
                    split = values_row.split(factor=0.9)

                    col_sliders = split.column(align=True)
                    # col_sliders.prop(addon_props, "uvisland_sizecheck_arearelative", text="Factor:")
                    col_sliders.prop(addon_props, "uvisland_sizecheck_area_pixelcoverage", text="Pixel Area (px²):")
                    col_sliders.prop(addon_props, "uvisland_sizecheck_area_pixelpercentage", text="Pixel Area %:")

                    col_locks = split.column(align=True)
                    # col_locks.prop(addon_props, "use_uvisland_sizecheck_arearelative", text="")
                    col_locks.prop(addon_props, "use_uvisland_sizecheck_area_pixelcoverage", text="")
                    col_locks.prop(addon_props, "use_uvisland_sizecheck_area_pixelpercentage", text="")

                    row = uv_island_thresholds_panel.row()
                    row.operator(SimpleToolbox_OT_UVCheckIslandThresholds.bl_idname)

        # ====== Find Modifiers ======
        if cat_show_find_modifiers_ops:
            find_modifiers_header, find_modifiers_panel = layout.panel(
                "simpletoolbox_pt_find_modifiers", default_closed=True
            )
            if find_modifiers_header:
                find_modifiers_header.label(text="Find Modifiers")

            if find_modifiers_panel:
                find_modifiers_panel_row = find_modifiers_panel.row()
                find_modifiers_panel_row.label(text="Name or Type (comma-separated):")
                find_modifiers_panel_row = find_modifiers_panel.row()
                find_modifiers_panel_row.prop(addon_props, "find_modifier_search_text", icon="SORTALPHA", text="")
                find_modifiers_panel_row.operator(
                    SimpleToolbox_OT_FindModifierSearch.bl_idname, icon="VIEWZOOM", text=""
                )

                if addon_prefs.experimental_features:
                    # Found objects UIList
                    find_modifiers_panel_row = find_modifiers_panel.row()
                    find_modifiers_panel_row.template_list(
                        "R0PROP_UL_FindModifierObjectsList",
                        "",
                        addon_find_modifier_props.objects_list,  # Collection owner
                        "found_objects",  # Collection property
                        addon_find_modifier_props.objects_list,  # Active item owner
                        "active_index",  # Active item property
                        rows=10,
                    )

        # ====== Object Sets Editor ======
        if cat_show_object_sets_editor:
            object_sets_header, object_sets_panel = layout.panel("simpletoolbox_pt_object_sets", default_closed=True)
            if object_sets_header:
                object_sets_header.label(text="Object Sets")

            if object_sets_panel:
                col = object_sets_panel.column()
                u.draw_objects_sets_uilist(col, context)

        # ====== Vertex Groups UI List ======
        if cat_show_vertex_groups_editor:
            vertex_groups_header, vertex_groups_panel = layout.panel(
                "simpletoolbox_pt_vertex_groups", default_closed=True
            )
            if vertex_groups_header:
                vertex_groups_header.label(text="Vertex Groups")

            if vertex_groups_panel:
                col = vertex_groups_panel.column()
                u.draw_vertex_groups_uilist(col, context)

        # if addon_prefs.experimental_features:
        # experimental_features_box = layout.box()
        # experimental_features_box.prop(addon_props, "show_experimental_features", icon="TRIA_DOWN" addon_props.show_experimental_features else "TRIA_RIGHT", emboss=False)
        # if addon_props.show_experimental_features:
        # ...

        # ====== Online Repository ======
        draw_repo_layout(layout, context)


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

# fmt: off
classes = [
    r0Tools_PT_SimpleToolbox, 
]
# fmt: on


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    # upd.trigger_update_check()
    upd.trigger_thread_update_check()


def unregister():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
