import bpy

_mod = "EDGE_DATA"

_most_used_indices = sorted(list({1, 2, 4, 6, 9, 14, 19}))
_precise_indices = sorted(list({i for i in range(0, 20, 1)} - set(_most_used_indices)))


def draw_edge_bweights_presets_uilist(layout, context, edge_bweights_box=None):
    """
    Draw the Edge Bevel Weights Presets UI list
    """
    from ..data_ops import SimpleToolbox_OT_ApplyBWeightValue
    from . import LOG, get_addon_prefs, get_addon_props

    addon_props = get_addon_props()
    addon_prefs = get_addon_prefs()

    grid_view = addon_prefs.edge_data_bweight_preset_grid_buttons_toggle

    # Edge Bevel Weights Presets parent layout
    if edge_bweights_box:
        parent = edge_bweights_box
    elif layout:
        parent = layout
    else:
        LOG(f"[ERROR] No valid layout to use:\n{layout=}\n{edge_bweights_box=}")
        return False

    # Presets Row Number Slider
    row = parent.row()

    if not grid_view:
        # Left Section - List
        row.template_list(
            "R0PROP_UL_EdgeBWeightsList",
            "edge_bweights_presets",
            addon_props.edge_bweights_presets,  # Collection owner
            "presets",  # Collection property
            addon_props.edge_bweights_presets,  # Active item owner
            "active_index",  # Active item property
            rows=10,
        )
    else:
        values = addon_props.edge_bweights_presets.presets

        row = parent.row()
        split = row.split(factor=0.4)

        # === Left Column: Most Used ===
        num_cols_most_used = 3
        most_used_box = split.box()
        most_used_col = most_used_box.column()

        row = most_used_col.row(align=True)
        for i, index in enumerate(_most_used_indices):
            # Every X items, create a new row
            if i > 0 and i % num_cols_most_used == 0:
                row = most_used_col.row(align=True)

            if index < len(values):
                preset = values[index]
                op = row.operator(SimpleToolbox_OT_ApplyBWeightValue.bl_idname, text=f"{preset.value:.2f}")
                op.value = preset.value

        # === Right Column: Precise ===
        num_cols_precise = 5
        precise_box = split.box()
        precise_col = precise_box.column()

        row = precise_col.row(align=True)
        for i, index in enumerate(_precise_indices):
            # Every X items, create a new row
            if i > 0 and i % num_cols_precise == 0:
                row = precise_col.row(align=True)

            if index < len(values):
                preset = values[index]
                op = row.operator(SimpleToolbox_OT_ApplyBWeightValue.bl_idname, text=f"{preset.value:.2f}")
                op.value = preset.value

        """
        for offset in range(0, len(values), 5):
            row = parent.row()
            for i in range(5):
                value = values[offset + i].value
                op = row.operator(SimpleToolbox_OT_ApplyBWeightValue.bl_idname, text=f"{value:.2f}")
                op.value = value
        """


@bpy.app.handlers.persistent
def initialize_bweight_presets(dummy):
    """Initialize bevel weight presets with default values"""
    from . import LOG, get_addon_props

    addon_props = get_addon_props()

    LOG(f"[INFO] [{_mod}] Initialising Edge Bevel Weight Presets")

    # Clear existing presets
    addon_props.edge_bweights_presets.presets.clear()

    # Add 0
    preset = addon_props.edge_bweights_presets.presets.add()
    preset.value = 0.0

    # Add preset values from 0.10 to 1.00 in steps of 0.05
    for i in range(10, 101, 5):
        preset = addon_props.edge_bweights_presets.presets.add()
        preset.value = round(i / 100.0, 2)
