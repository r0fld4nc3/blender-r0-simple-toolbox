import bpy

from .const import INTERNAL_NAME, ADDON_NAME, VERSION_STR
from . import utils as u

class PT_SimpleToolbox(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_quick_toolbox'
    bl_label = f'{ADDON_NAME} ({VERSION_STR})'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    # bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        addon_props = context.scene.r0fl_toolbox_props
        addon_prefs = bpy.context.preferences.addons[INTERNAL_NAME].preferences
        
        layout = self.layout

        row = layout.row()
        row.prop(addon_prefs, "experimental_features", text="Experimental Features", icon="EXPERIMENTAL")

        box = layout.box()
        box.prop(addon_props, "show_dev_tools", icon="TRIA_DOWN" if addon_props.show_dev_tools else "TRIA_RIGHT", emboss=False)
        if addon_props.show_dev_tools:
            row = box.row()
            row.operator("script.reload", text="Reload All Scripts", icon="NONE")
            box = box.box()
            row = box.row()
            row.prop(addon_props, "reload_modules_prop")
            row = box.row()
            row.operator("r0tools.reload_named_scripts", icon="NONE")
        
        # Object Ops
        box = layout.box()
        box.prop(addon_props, "show_object_ops", icon="TRIA_DOWN" if addon_props.show_object_ops else "TRIA_RIGHT", emboss=False)
        if addon_props.show_object_ops:
            # row = box.row(align=True)
            # row.label(text="Object Ops")
            row = box.row(align=True)
            row.operator("r0tools.clear_custom_split_normals")
            # row = box.row(align=True)
            # row.operator("r0tools.clear_mesh_attributes")
            row = box.row(align=True)
            row.operator("r0tools.clear_all_objects_children")
            row = box.row()
            row.prop(addon_props, "show_custom_property_list_prop", icon="TRIA_DOWN" if addon_props.show_custom_property_list_prop else "TRIA_RIGHT", emboss=False)
            # Scrollable list with checkboxes
            if addon_props.show_custom_property_list_prop:
                row = box.row()
                row.template_list(
                    "RPROP_UL_custom_property_list",
                    "custom_property_list",
                    context.scene.r0fl_toolbox_props,  # Collection owner
                    "custom_property_list",            # Collection property
                    context.scene.r0fl_toolbox_props,  # Active item owner
                    "custom_property_list_index",      # Active item property
                    rows=6
                )
                row = box.row()
                row.operator("r0tools.clear_custom_properties")
        
        # Mesh Ops
        box = layout.box()
        box.prop(addon_props, "show_mesh_ops", icon="TRIA_DOWN" if addon_props.show_mesh_ops else "TRIA_RIGHT", emboss=False)
        if addon_props.show_mesh_ops:
            # row = box.row(align=True)
            # row.label(text="Mesh Ops")
            # Nth Edges Operator
            row = box.row(align=True)
            row.operator("r0tools.nth_edges")
            box = box.box()
            row = box.row(align=True)
            # Clear Sharp Edges on Axis
            row.label(text="Clear Sharp Edges on Axis:")
            row = box.row(align=True)
            row.prop(addon_prefs, "clear_sharp_axis_float_prop", text="Threshold")
            row = box.row(align=True)
            row.scale_x = 5
            row.operator("r0tools.clear_sharp_axis_x", text="X")
            row.operator("r0tools.clear_sharp_axis_y", text="Y")
            row.operator("r0tools.clear_sharp_axis_z", text="Z")
        
        # Externals
        box = layout.box()
        box.prop(addon_props, "show_ext_ops", icon="TRIA_DOWN" if addon_props.show_ext_ops else "TRIA_RIGHT", emboss=False)
        if addon_props.show_ext_ops:
            row = box.row(align=True)
            row.label(text="ZenUV Texel Density")
            row = box.row(align=True)
            row.prop(addon_prefs, "zenuv_td_prop", text="TD:")
            row.prop(addon_prefs, "zenuv_td_unit_prop", text="Unit")
            row = box.row(align=True)
            row.operator("r0tools.zenuv_set_td")

        if addon_prefs.experimental_features:
            row = layout.row()
            row.label(text="EXPERIMENTAL", icon="EXPERIMENTAL")
            box = layout.box()
            row = box.row()
            row.label(text="LODs")
            row = box.row()
            row.operator("r0tools.experimental_op_1")
            row = box.row()
            row.prop(addon_props, "screen_size_pct_prop", text="Screen Size (%):")


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = [
    PT_SimpleToolbox
]

depsgraph_handlers = [
    u.continuous_property_list_update
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    for handler in depsgraph_handlers:
        if handler not in bpy.app.handlers.depsgraph_update_post:
            print(f"[DEBUG] Registering Handler {handler}")
            bpy.app.handlers.depsgraph_update_post.append(handler)

def unregister():
    for handler in depsgraph_handlers:
        try:
            if handler in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.remove(handler)
        except Exception as e:
            print(f"Error removing handler {handler}: {e}")

    for cls in classes:
        bpy.utils.unregister_class(cls)
