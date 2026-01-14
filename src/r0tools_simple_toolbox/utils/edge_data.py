import logging

import bpy

log = logging.getLogger(__name__)


# @bpy.app.handlers.persistent
def initialize_bweight_presets(dummy):
    """Initialize bevel weight presets with default values"""
    from . import get_addon_edge_data_props

    addon_edge_data_props = get_addon_edge_data_props()

    log.info(f"Initialising Edge Bevel Weight Presets")

    # Clear existing presets
    addon_edge_data_props.edge_bweights_presets.presets.clear()

    # Add 0
    preset = addon_edge_data_props.edge_bweights_presets.presets.add()
    preset.value = 0.0

    # Add preset values from 0.10 to 1.00 in steps of 0.05
    for i in range(10, 101, 5):
        preset = addon_edge_data_props.edge_bweights_presets.presets.add()
        preset.value = round(i / 100.0, 2)

    log.info(f"Preset: {[round(v.value, 2) for v in addon_edge_data_props.edge_bweights_presets.presets]}")
