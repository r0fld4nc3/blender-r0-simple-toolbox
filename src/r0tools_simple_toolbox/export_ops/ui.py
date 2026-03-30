import logging

import bpy

from .. import utils as u
from ..defines import ADDON_CATEGORY, ADDON_NAME_BARE, IDNAME_EXTRA
from .operators import *

log = logging.getLogger(__name__)


class r0Tools_PT_SimpleToolboxQuickExportOps(bpy.types.Panel):
    bl_idname = "OBJECT_PT_simple_toolbox_quick_export_ops"
    bl_label = f"Quick Export - {ADDON_NAME_BARE}{IDNAME_EXTRA}"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"
    bl_options = {"DEFAULT_CLOSED", "INSTANCED"}
    bl_order = 4

    @classmethod
    def poll(cls, context):
        addon_prefs = u.get_addon_prefs()
        addon_props = u.get_addon_props()
        experimental_enabled = addon_prefs.experimental_features
        show_panel = addon_props.cat_show_quick_export_panel

        return experimental_enabled and show_panel

    def draw(self, context):
        layout = self.layout

        layout.label(text="Quick Export (FBX)")

        u.draw_quick_export_sets_uilist(layout, context)


classes = []
_panel_classes: list[type] = []


def register_panels():
    global _panel_classes
    _panel_classes.clear()

    addon_prefs = u.get_addon_prefs()

    panel_attributions = {
        r0Tools_PT_SimpleToolboxQuickExportOps: {
            "categories": addon_prefs.panel_attributions_export_ops,
            "defaults_rna": addon_prefs.bl_rna.properties["panel_attributions_export_ops"].default,
        }
    }

    for panel_class, values in panel_attributions.items():
        categories = values.get("categories", [])

        for category in u.parse_comma_separated_list(categories, default=values.get("defaults_rna", ADDON_CATEGORY)):
            variant = u.create_panel_variant(panel_class, category=category)
            _panel_classes.append(variant)

    for cls in _panel_classes:
        bpy.utils.register_class(cls)


def unregister_panels():
    global _panel_classes

    for cls in reversed(_panel_classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError as e:
            log.error(e)

    _panel_classes.clear()


def register():
    classes.clear()  # Prevent duplicates

    register_panels()

    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    unregister_panels()

    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    classes.clear()
