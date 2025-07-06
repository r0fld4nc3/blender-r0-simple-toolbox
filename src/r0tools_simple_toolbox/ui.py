import bpy

from . import ext_update as upd
from . import utils as u
from .data_ops import SimpleToolbox_OT_EdgeDataToVertexColour
from .defines import ADDON_NAME, VERSION_STR
from .operators import *
from .repo import draw_repo_layout

_mod = "UI"

# fmt: off
class r0Tools_PT_SimpleToolbox(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_simple_toolbox'
    bl_label = f'{ADDON_NAME} ({VERSION_STR})'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
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
        experimental_props = u.get_addon_experimental_props()
        
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
            update_row.operator(SimpleToolbox_OT_TakeMeToUpdate.bl_idname, text="Take me there!", icon="INDIRECT_ONLY_ON")

        # ====== Dev Tools ======
        if addon_prefs.dev_tools:
            dev_tools_box = layout.box()
            dev_tools_box.prop(addon_props, "show_dev_tools", icon="TRIA_DOWN" if addon_props.show_dev_tools else "TRIA_RIGHT", emboss=False)
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

        # ====== Find Modifiers on Objects ======
        if cat_show_find_modifiers_ops and not cat_show_object_ops:
            find_modifiers_box = layout.box()
            row = find_modifiers_box.row()
            row.prop(addon_props, "show_find_modifier_search", icon="TRIA_DOWN" if addon_props.show_find_modifier_search else "TRIA_RIGHT", emboss=False)
            if addon_props.show_find_modifier_search:
                row = find_modifiers_box.row()
                row.label(text="Name or Type:")
                row = find_modifiers_box.row()
                row.prop(addon_props, "find_modifier_search_text", icon="SORTALPHA", text="")
                row.operator(SimpleToolbox_OT_FindModifierSearch.bl_idname, icon="VIEWZOOM", text="")
        
        # ====== Object Ops ======
        if cat_show_object_ops:
            object_ops_box = layout.box()
            object_ops_box.prop(addon_props, "show_object_ops", icon="TRIA_DOWN" if addon_props.show_object_ops else "TRIA_RIGHT", emboss=False)
            if addon_props.show_object_ops:
                # >> Row
                row = object_ops_box.row(align=True)
                row_split = row.split(align=True)
                # Clear Split Normals Data
                row_split.operator(SimpleToolbox_OT_ClearCustomSplitNormalsData.bl_idname)
                # Clear Objects Children
                row_split.operator(SimpleToolbox_OT_ClearChildrenRecurse.bl_idname)
                
                # >> Row
                row = object_ops_box.row(align=True)
                row_split = row.split(align=True)
                # Select Empty Objects
                row_split.operator(SimpleToolbox_OT_SelectEmptyObjects.bl_idname)

                # >> Row
                row = object_ops_box.row(align=True)
                row_split = row.split(align=True)
                # Remove unused Materials
                row_split.operator(SimpleToolbox_OT_RemoveUnusedMaterials.bl_idname)

                # ====== Find Modifiers on Objects ======
                # Kept here as it can be group into object ops, if possible.
                # Kept above as well in case the Object Ops is not visible
                if cat_show_find_modifiers_ops and cat_show_object_ops:
                    find_modifiers_box = object_ops_box.box()
                    row = find_modifiers_box.row()
                    row.prop(addon_props, "show_find_modifier_search", icon="TRIA_DOWN" if addon_props.show_find_modifier_search else "TRIA_RIGHT", emboss=False)
                    if addon_props.show_find_modifier_search:
                        row = find_modifiers_box.row()
                        row.label(text="Name or Type:")
                        row = find_modifiers_box.row()
                        row.prop(addon_props, "find_modifier_search_text", icon="SORTALPHA", text="")
                        row.operator(SimpleToolbox_OT_FindModifierSearch.bl_idname, icon="VIEWZOOM", text="")

                # ====== Custom Properties UI List ======
                # Kept here as it can be group into object ops, if possible.
                # Kept outside as well in case the Object Ops is not visible
                if cat_show_custom_properties_editor and cat_show_object_ops:
                    custom_properties_box = object_ops_box.box()
                    row = custom_properties_box.row()
                    row.prop(addon_props, "show_custom_property_list_prop", icon="TRIA_DOWN" if addon_props.show_custom_property_list_prop else "TRIA_RIGHT", emboss=False)
                    if addon_props.show_custom_property_list_prop:
                        # Row Number Slider
                        row = custom_properties_box.row()
                        split = row.split(factor=0.35)
                        split.prop(addon_prefs, "custom_properties_list_rows", text="Rows:")
                        
                        row = custom_properties_box.row()
                        row.template_list(
                            "R0PROP_UL_CustomPropertiesList",
                            "custom_property_list",
                            u.get_addon_props(),           # Collection owner
                            "custom_property_list",        # Collection property
                            u.get_addon_props(),           # Active item owner
                            "custom_property_list_index",  # Active item property
                            rows=addon_prefs.custom_properties_list_rows
                        )
                        # Clear Custom Properties
                        row = custom_properties_box.row()
                        row.operator(SimpleToolbox_OT_ClearCustomProperties.bl_idname)


        # ====== Object Sets Editor ======
        if cat_show_object_sets_editor:
            object_sets_box = layout.box()
            row = object_sets_box.row()
            row.prop(addon_props, "show_object_sets", icon="TRIA_DOWN" if addon_props.show_object_sets else "TRIA_RIGHT", emboss=False)
            if addon_props.show_object_sets:
                u.draw_objects_sets_uilist(self.layout, context, object_sets_box=object_sets_box)


        # ====== Vertex Groups UI List ======
        if cat_show_vertex_groups_editor:
            vertex_groups_box = layout.box()
            row = vertex_groups_box.row()
            row.prop(addon_props, "show_vertex_groups", icon="TRIA_DOWN" if addon_props.show_vertex_groups else "TRIA_RIGHT", emboss=False)
            if addon_props.show_vertex_groups:
                u.draw_vertex_groups_uilist(self.layout, context, vertex_groups_box=vertex_groups_box)

        
        # ====== Mesh Ops ======
        if cat_show_mesh_ops:
            mesh_ops_box = layout.box()
            mesh_ops_box.prop(addon_props, "show_mesh_ops", icon="TRIA_DOWN" if addon_props.show_mesh_ops else "TRIA_RIGHT", emboss=False)
            if addon_props.show_mesh_ops:
                # >> Row
                row = mesh_ops_box.row(align=True)
                row_split = row.split(align=True)
                # Remove Nth Edges Operator
                row_split.operator(SimpleToolbox_OT_DissolveNthEdge.bl_idname)
                if addon_prefs.experimental_features:
                    row_split.operator(SimpleToolbox_OT_RestoreNthEdge.bl_idname)

                # >> Row
                row = mesh_ops_box.row(align=True)
                row.operator(SimpleToolbox_OT_ResetEdgeData.bl_idname)

                # >> Row
                row = mesh_ops_box.row(align=True)
                row_split = row.split(align=True)
                # Restore rotation from Selection
                row_split.operator(SimpleToolbox_OT_RestoreRotationFromSelection.bl_idname)
                
                # Clear Sharp Edges on Axis
                clear_sharp_edges_box = mesh_ops_box.box()
                row = clear_sharp_edges_box.row(align=True)
                clear_sharp_edges_box.prop(addon_props, "show_clear_sharps_on_axis", icon="TRIA_DOWN" if addon_props.show_clear_sharps_on_axis else "TRIA_RIGHT", emboss=False)
                if addon_props.show_clear_sharps_on_axis:
                    row = clear_sharp_edges_box.row(align=True)
                    row.prop(addon_prefs, "clear_sharp_axis_float_prop", text="Threshold")
                    row = clear_sharp_edges_box.row(align=True)
                    row.scale_x = 5
                    row.operator(SimpleToolbox_OT_ClearAxisSharpEdgesX.bl_idname, text="X")
                    row.operator(SimpleToolbox_OT_ClearAxisSharpEdgesY.bl_idname, text="Y")
                    row.operator(SimpleToolbox_OT_ClearAxisSharpEdgesZ.bl_idname, text="Z")

        # ====== Custom Properties UI List ======
        if cat_show_custom_properties_editor and not cat_show_object_ops:
            custom_properties_box = layout.box()
            row = custom_properties_box.row()
            row.prop(addon_props, "show_custom_property_list_prop", icon="TRIA_DOWN" if addon_props.show_custom_property_list_prop else "TRIA_RIGHT", emboss=False)
            if addon_props.show_custom_property_list_prop:
                # Row Number Slider
                row = custom_properties_box.row()
                split = row.split(factor=0.35)
                split.prop(addon_prefs, "custom_properties_list_rows", text="Rows:")
                
                row = custom_properties_box.row()
                row.template_list(
                    "R0PROP_UL_CustomPropertiesList",
                    "custom_property_list",
                    u.get_addon_props(),           # Collection owner
                    "custom_property_list",        # Collection property
                    u.get_addon_props(),           # Active item owner
                    "custom_property_list_index",  # Active item property
                    rows=addon_prefs.custom_properties_list_rows
                )
                # Clear Custom Properties
                row = custom_properties_box.row()
                row.operator(SimpleToolbox_OT_ClearCustomProperties.bl_idname)
        
        # ====== UV Ops ======
        if cat_show_uv_ops:
            uv_ops_box = layout.box()
            uv_ops_box.prop(addon_props, "show_uv_ops", icon="TRIA_DOWN" if addon_props.show_uv_ops else "TRIA_RIGHT", emboss=False)
            if addon_props.show_uv_ops:
                # UV Map Target Resolution
                uv_map_resolution_box = uv_ops_box.box()
                row = uv_map_resolution_box.row()
                row.label(text="UV Map")

                dropdown_col = uv_map_resolution_box.column(align=True)
                dropdown_col.prop(addon_props, "uv_size_x", text="Width")
                dropdown_col.prop(addon_props, "uv_size_y", text="Height")

                # UV Island Thresholds
                uv_island_checks_thresholds_box = uv_ops_box.box()
                uv_island_checks_thresholds_box.prop(addon_props, "show_uv_island_area_thresholds", icon="TRIA_DOWN" if addon_props.show_uv_island_area_thresholds else "TRIA_RIGHT", emboss=False)
                if addon_props.show_uv_island_area_thresholds:
                    values_row = uv_island_checks_thresholds_box.row()
                    split = values_row.split(factor=0.9)

                    col_sliders = split.column(align=True)
                    # col_sliders.prop(addon_props, "uvisland_sizecheck_arearelative", text="Factor:")
                    col_sliders.prop(addon_props, "uvisland_sizecheck_area_pixelcoverage", text="Pixel Area (px²):")
                    col_sliders.prop(addon_props, "uvisland_sizecheck_area_pixelpercentage", text="Pixel Area %:")
                    
                    col_locks = split.column(align=True)
                    # col_locks.prop(addon_props, "use_uvisland_sizecheck_arearelative", text="")
                    col_locks.prop(addon_props, "use_uvisland_sizecheck_area_pixelcoverage", text="")
                    col_locks.prop(addon_props, "use_uvisland_sizecheck_area_pixelpercentage", text="")
                    
                    row = uv_island_checks_thresholds_box.row()
                    row.operator(SimpleToolbox_OT_UVCheckIslandThresholds.bl_idname)

        if addon_prefs.experimental_features:
            experimental_features_box = layout.box()
            experimental_features_box.prop(addon_props, "show_experimental_features", icon="TRIA_DOWN" if addon_props.show_experimental_features else "TRIA_RIGHT", emboss=False)
            if addon_props.show_experimental_features:
                exp_edge_data_row = experimental_features_box.row()
                exp_edge_data_row.prop(experimental_props, "show_edge_data_ops", icon="TRIA_DOWN" if experimental_props.show_edge_data_ops else "TRIA_RIGHT", emboss=False)
                if experimental_props.show_edge_data_ops:
                    row = experimental_features_box.row()
                    row.operator(SimpleToolbox_OT_EdgeDataToVertexColour.bl_idname, icon="GROUP_VCOL")
                    row = experimental_features_box.row()
                    bweight_presets_box = row.box()
                    row = bweight_presets_box.row()
                    row.prop(addon_prefs, "edge_data_bweight_preset_grid_buttons_toggle", icon="MESH_GRID", text="")
                    row.label(text=f"{'Bevel Weight Preset Grid' if addon_prefs.edge_data_bweight_preset_grid_buttons_toggle else 'Bevel Weight Preset List'}")
                    u.draw_edge_bweights_presets_uilist(self.layout, context, edge_bweights_box=bweight_presets_box)

        # ====== Online Repository ======
        draw_repo_layout(layout, context)
# fmt: on


class r0Tools_PT_SimpleToolboxEdgeDataOps(bpy.types.Panel):
    bl_idname = "OBJECT_PT_simple_toolbox_edge_data"
    bl_label = f"Edge Data Ops ({VERSION_STR})"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"
    # bl_options = {"DEFAULT_CLOSED"}
    has_update = False

    def draw(self, context):
        addon_props = u.get_addon_props()
        addon_prefs = u.get_addon_prefs()

        layout = self.layout

        if addon_prefs.experimental_features:
            row = layout.row()
            row.operator(SimpleToolbox_OT_EdgeDataToVertexColour.bl_idname, icon="GROUP_VCOL")
            row = layout.row()
            bweight_presets_box = row.box()
            row = bweight_presets_box.row()
            row.prop(addon_prefs, "edge_data_bweight_preset_grid_buttons_toggle", icon="MESH_GRID", text="")
            row.label(
                text=f"{'Bevel Weight Preset Grid' if addon_prefs.edge_data_bweight_preset_grid_buttons_toggle else 'Bevel Weight Preset List'}"
            )
            u.draw_edge_bweights_presets_uilist(self.layout, context, edge_bweights_box=bweight_presets_box)


def unregister():
    for cls in classes:
        print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    bpy.types.VIEW3D_PT_transform.remove(u.draw_bweights_in_transform_panel)


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = [r0Tools_PT_SimpleToolbox, r0Tools_PT_SimpleToolboxEdgeDataOps]


def register():
    for cls in classes:
        print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    # upd.trigger_update_check()
    upd.trigger_thread_update_check()


def unregister():
    for cls in classes:
        print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
