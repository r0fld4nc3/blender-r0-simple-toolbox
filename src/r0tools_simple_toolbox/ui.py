import bpy

from . import ext_update as upd
from . import utils as u
from .defines import ADDON_NAME, VERSION_STR
from .repo import draw_repo_layout


# fmt: off
class r0Tools_PT_SimpleToolbox(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_quick_toolbox'
    bl_label = f'{ADDON_NAME} ({VERSION_STR})'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    # bl_options = {"DEFAULT_CLOSED"}
    has_update = False

    
    @classmethod
    def _update_callback(cls, result):
        cls.has_update = result

    
    def draw(self, context):
        addon_props = u.get_addon_props()
        addon_prefs = u.get_addon_prefs()
        
        layout = self.layout

        row = layout.row()
        row.prop(addon_prefs, "dev_tools", text="Dev Tools", icon="TOOL_SETTINGS")
        row.prop(addon_prefs, "experimental_features", text="Experimental", icon="EXPERIMENTAL")

        if self.has_update:
            update_box = layout.box()
            update_row = update_box.row(align=True)
            update_row.label(text="", icon="FUND")
            update_row.label(text="UPDATE AVAILABLE", icon="FILE_REFRESH")
            update_row.label(text="", icon="FUND")

        # ====== Dev Tools ======
        if addon_prefs.dev_tools:
            dev_tools_box = layout.box()
            dev_tools_box.prop(addon_props, "show_dev_tools", icon="TRIA_DOWN" if addon_props.show_dev_tools else "TRIA_RIGHT", emboss=False)
            if addon_props.show_dev_tools:
                row = dev_tools_box.row()
                row.operator("script.reload", text="Reload All Scripts", icon="PACKAGE")
                reload_user_defined_box = dev_tools_box.box()
                row = reload_user_defined_box.row()
                row.prop(addon_props, "reload_modules_prop")
                row = reload_user_defined_box.row()
                row.operator("r0tools.reload_named_scripts", icon="TOOL_SETTINGS")
                if addon_prefs.experimental_features:
                    row = dev_tools_box.row()
                    row.operator("image.reload", icon="IMAGE_DATA")
                row = dev_tools_box.row()
                row.prop(addon_prefs, "debug", text="Debug", icon="EXPERIMENTAL")
        
        # ====== Object Ops ======
        object_ops_box = layout.box()
        object_ops_box.prop(addon_props, "show_object_ops", icon="TRIA_DOWN" if addon_props.show_object_ops else "TRIA_RIGHT", emboss=False)
        if addon_props.show_object_ops:
            # Clear Split Normals Data
            row = object_ops_box.row(align=True)
            row.operator("r0tools.clear_custom_split_normals_data")

            # Select Empty Objects
            row = object_ops_box.row(align=True)
            row.operator("r0tools.select_empty_objects")

            # Clear Objects Children
            row = object_ops_box.row(align=True)
            row.operator("r0tools.clear_all_objects_children")

            # Find Modifiers on Objects
            find_modifiers_box = object_ops_box.box()
            row = find_modifiers_box.row()
            row.prop(addon_props, "show_find_modifier_search", icon="TRIA_DOWN" if addon_props.show_find_modifier_search else "TRIA_RIGHT", emboss=False)
            if addon_props.show_find_modifier_search:
                row = find_modifiers_box.row()
                row.label(text="Name or Type:")
                row = find_modifiers_box.row()
                row.prop(addon_props, "find_modifier_search_text", icon="SORTALPHA", text="")
                row.operator("r0tools.find_modifier_search", icon="VIEWZOOM", text="")
            
            # Object Sets Editor
            object_sets_box = object_ops_box.box()
            row = object_sets_box.row()
            row.prop(addon_props, "show_object_sets", icon="TRIA_DOWN" if addon_props.show_object_sets else "TRIA_RIGHT", emboss=False)
            if addon_props.show_object_sets:
                u.draw_objects_sets_uilist(self.layout, context, object_sets_box=object_sets_box)

            # Custom Properties UI List
            custom_properties_box = object_ops_box.box()
            row = custom_properties_box.row()
            row.prop(addon_props, "show_custom_property_list_prop", icon="TRIA_DOWN" if addon_props.show_custom_property_list_prop else "TRIA_RIGHT", emboss=False)
            if addon_props.show_custom_property_list_prop:
                # row = custom_properties_box.row()
                # Row Number Slider (Same as in addon preferences)
                # row.prop(addon_prefs, "custom_properties_list_rows", text="Rows:")
                
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
                row.operator("r0tools.delete_custom_properties")
        
        # ====== Mesh Ops ======
        mesh_ops_box = layout.box()
        mesh_ops_box.prop(addon_props, "show_mesh_ops", icon="TRIA_DOWN" if addon_props.show_mesh_ops else "TRIA_RIGHT", emboss=False)
        if addon_props.show_mesh_ops:
            # Nth Edges Operator
            row = mesh_ops_box.row(align=True)
            row.operator("r0tools.nth_edges")
            row = mesh_ops_box.row(align=True)
            row.operator("r0tools.rotation_from_selection")
            
            # Clear Sharp Edges on Axis
            clear_sharp_edges_box = mesh_ops_box.box()
            row = clear_sharp_edges_box.row(align=True)
            clear_sharp_edges_box.prop(addon_props, "show_clear_sharps_on_axis", icon="TRIA_DOWN" if addon_props.show_clear_sharps_on_axis else "TRIA_RIGHT", emboss=False)
            if addon_props.show_clear_sharps_on_axis:
                row = clear_sharp_edges_box.row(align=True)
                row.prop(addon_prefs, "clear_sharp_axis_float_prop", text="Threshold")
                row = clear_sharp_edges_box.row(align=True)
                row.scale_x = 5
                row.operator("r0tools.clear_sharp_axis_x", text="X")
                row.operator("r0tools.clear_sharp_axis_y", text="Y")
                row.operator("r0tools.clear_sharp_axis_z", text="Z")
        
        # ====== UV Ops ======
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
                row.operator("r0tools.uv_check_island_thresholds")

        # ====== Online Repository ======
        draw_repo_layout(layout, context)

        # ====== Heavy Experimentals ======
        if addon_prefs.experimental_features:
            experimental_ops_box = layout.box()
            experimental_ops_box.prop(addon_props, "show_experimental_features", icon="TRIA_DOWN" if addon_props.show_experimental_features else "TRIA_RIGHT", emboss=False)
            if addon_props.show_experimental_features:
                lods_box = experimental_ops_box.box()
                row = lods_box.row()
                row.label(text="LODs")
                row = lods_box.row()
                row.operator("r0tools.experimental_op_1")
                row = lods_box.row()
                row.prop(addon_props, "screen_size_pct_prop", text="Screen Size (%):")
# fmt: on


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = [r0Tools_PT_SimpleToolbox]


def register():
    for cls in classes:
        print(f"[UI] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    upd.trigger_update_check()


def unregister():
    for cls in classes:
        print(f"[UI] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
