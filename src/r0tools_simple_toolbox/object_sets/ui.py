import bpy

from .. import utils as u
from ..defines import ADDON_CATEGORY, ADDON_NAME_BARE, IDNAME_EXTRA
from . import _mod as parent_mod
from .operators import *

_mod = f"{parent_mod}.UI"


class r0Tools_PT_SimpleToolboxObjectSets(bpy.types.Panel):
    bl_idname = "OBJECT_PT_simple_toolbox_object_sets"
    bl_label = f"Object Sets - {ADDON_NAME_BARE}{IDNAME_EXTRA}"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ADDON_CATEGORY
    bl_options = {"DEFAULT_CLOSED", "INSTANCED"}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        addon_props = u.get_addon_props()

        return addon_props.cat_show_object_sets_editor

    def draw(self, context):
        layout = self.layout
        u.draw_objects_sets_uilist(layout, context)


classes = []

# fmt: off
panel_attributions = {
    r0Tools_PT_SimpleToolboxObjectSets: {
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
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
