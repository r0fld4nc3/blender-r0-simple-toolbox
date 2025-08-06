import bpy

from .. import utils as u
from ..defines import ADDON_CATEGORY, ADDON_NAME_BARE, DEBUG, IDNAME_EXTRA
from . import _mod as parent_mod
from .operators import *

_mod = f"{parent_mod}.UI"

_most_used_indices = sorted(list({1, 2, 4, 6, 9, 14, 19}))
_precise_indices = sorted(list({i for i in range(0, 20, 1)} - set(_most_used_indices)))


class r0Tools_PT_SimpleToolboxEdgeDataOps(bpy.types.Panel):
    bl_idname = "OBJECT_PT_simple_toolbox_edge_data"
    bl_label = f"Edge Data - {ADDON_NAME_BARE}.{IDNAME_EXTRA}"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"
    bl_options = {"DEFAULT_CLOSED", "INSTANCED"}
    bl_order = 3

    @classmethod
    def poll(cls, context):
        addon_prefs = u.get_addon_prefs()
        addon_props = u.get_addon_props()
        experimental_enabled = addon_prefs.experimental_features
        show_panel = addon_props.cat_show_edge_data_panel

        return experimental_enabled and show_panel

    def draw(self, context):
        layout = self.layout
        draw_edge_data_panel_ui(layout, context)


def draw_edge_bweights_presets_operators(layout, context):
    """
    Draw the Edge Bevel Weights Presets UI list
    """
    from ..data_ops import (
        SimpleToolbox_OT_ApplyBWeightPreset,
        SimpleToolbox_OT_SelectColourAttributeLayer,
    )
    from ..utils import LOG, get_addon_edge_data_props, get_addon_prefs, get_addon_props

    addon_prefs = get_addon_prefs()
    addon_edge_data_props = get_addon_edge_data_props()

    alt_view = addon_prefs.edge_data_bweight_presets_alt_view

    row = layout.row()
    row.prop(addon_prefs, "edge_data_bweight_presets_alt_view", icon="MESH_GRID", text="")
    row.label(
        text=f"{'Bevel Weight Presets' if not addon_prefs.edge_data_bweight_presets_alt_view else 'Bevel Weight Presets Alternative'}"
    )

    # Where to apply to
    row = layout.row(align=True)
    row.prop(addon_edge_data_props, "apply_as_bevel_weights", toggle=True)
    # row = layout.row()
    row.prop(addon_edge_data_props, "apply_as_creases", toggle=True)

    # Layer to select
    row = layout.row(align=True)
    op = row.operator(SimpleToolbox_OT_SelectColourAttributeLayer.bl_idname, text="Select Bevel Layer")
    op.select_bevel_layer = True
    op.select_crease_layer = False
    op = row.operator(SimpleToolbox_OT_SelectColourAttributeLayer.bl_idname, text="Select Crease Layer")
    op.select_bevel_layer = False
    op.select_crease_layer = True

    row = layout.row()

    values = addon_edge_data_props.edge_bweights_presets.presets

    if not alt_view:
        row = layout.row()
        split = row.split(factor=0.45)

        # === Left Column: Most Used ===
        num_cols_most_used = 2
        most_used_box = split.box()
        most_used_col = most_used_box.column()

        row = most_used_col.row(align=True)
        for i, index in enumerate(_most_used_indices):
            # Every X items, create a new row
            if i > 0 and i % num_cols_most_used == 0:
                row = most_used_col.row(align=True)

            if index < len(values):
                preset = values[index]
                value = f"{preset.value*100:.2f}".split(".")[0] + "%"
                op = row.operator(SimpleToolbox_OT_ApplyBWeightPreset.bl_idname, text=value)
                op.value = preset.value

        # === Right Column: Precise ===
        num_cols_precise = 3
        precise_box = split.box()
        precise_col = precise_box.column()

        row = precise_col.row(align=True)
        for i, index in enumerate(_precise_indices):
            # Every X items, create a new row
            if i > 0 and i % num_cols_precise == 0:
                row = precise_col.row(align=True)

            if index < len(values):
                preset = values[index]
                value = f"{preset.value*100:.2f}".split(".")[0] + "%"
                op = row.operator(SimpleToolbox_OT_ApplyBWeightPreset.bl_idname, text=value)
                op.value = preset.value
    else:
        # Grid flow with 2 columns
        grid_flow = layout.grid_flow(row_major=False, columns=2, even_columns=True, even_rows=False, align=True)

        for preset in values:
            value_text = f"{preset.value*100:.2f}".split(".")[0] + "%"
            op = grid_flow.operator(SimpleToolbox_OT_ApplyBWeightPreset.bl_idname, text=value_text)
            op.value = preset.value


def draw_edge_data_panel_ui(layout, context):
    from ..data_ops import SimpleToolbox_OT_EdgeDataToVertexColour
    from ..utils import LOG, get_addon_edge_data_props, get_addon_prefs, get_addon_props

    addon_edge_data_props = get_addon_edge_data_props()

    row = layout.row()
    row.prop(addon_edge_data_props, "convert_using_max_value")

    row = layout.row()
    row.scale_y = 2
    row.operator(SimpleToolbox_OT_EdgeDataToVertexColour.bl_idname, icon="GROUP_VCOL")
    row = layout.row()
    row.label(text="Convert:")
    row = layout.row(align=True)
    row.prop(addon_edge_data_props, "bevel_weights_to_vcol", toggle=True)
    row.prop(addon_edge_data_props, "crease_to_vcol", toggle=True)
    row = layout.row()

    draw_edge_bweights_presets_operators(layout, context)


classes = []

# fmt: off
panel_attributions = {
    r0Tools_PT_SimpleToolboxEdgeDataOps: {
        "categories": [ADDON_CATEGORY, "Item"]
    }
}
# fmt : on


def register():
    for panel_class, values in panel_attributions.items():
        categories = values.get("categories")
        for cat in categories:
            variant = u.create_panel_variant(panel_class, category=cat)
            classes.append(variant)

    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
