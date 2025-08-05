import bpy

from .. import utils as u
from ..defines import ADDON_CATEGORY, ADDON_NAME_BARE, DEBUG, IDNAME_EXTRA
from . import _mod as parent_mod
from .operators import *

_mod = f"{parent_mod}.UI"


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
        u.draw_edge_data_panel_ui(layout, context)


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
