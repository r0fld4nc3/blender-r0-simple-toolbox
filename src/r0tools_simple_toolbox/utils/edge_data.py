import bpy

_mod = "EDGE_DATA"


def draw_edge_bweights_presets_uilist(layout, context, edge_bweights_box=None):
    """
    Draw the Edge Bevel Weights Presets UI list
    """
    from ..bake_ops import SimpleToolbox_OT_ApplyBWeightPreset
    from . import LOG, get_addon_props

    addon_props = get_addon_props()

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
        preset.value = i / 100.0
