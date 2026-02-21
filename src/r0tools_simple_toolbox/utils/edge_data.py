import logging

import bpy

from .. import utils as u
from . import get_addon_edge_data_props

log = logging.getLogger(__name__)

_initialised: bool = False


@bpy.app.handlers.persistent
def initialize_bweight_presets(dummy):
    """Initialize bevel weight presets with default values"""

    # Test if values are empty, only run after initialised
    # Fixes a specific error that seemed to occur when loading
    # Blend files higher than the current Blender version
    # i.e.: Blender 4.5.3 loads file from 5.x.x
    # For that let's get the file version first
    global _initialised
    if _initialised:
        if not u.file_version_greater_than_blender_version(compare_major=True):
            # File version is not greater than Blender version, skip re-init.
            log.info("Skip bweight re-init")
            return
        else:
            # File version is greater than Blender version, force re-init.
            log.info("Force bweight re-init")

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

    # Set initialised
    _initialised = True
