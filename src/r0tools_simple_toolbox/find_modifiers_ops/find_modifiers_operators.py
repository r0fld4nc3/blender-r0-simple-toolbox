import logging

import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)

from .. import utils as u

log = logging.getLogger(__name__)


class SimpleToolbox_OT_FindModifiersCategoryVisCollapse(bpy.types.Operator):
    bl_label = "Toggle All Categories"
    bl_idname = "r0tools.find_modifiers_collapse_categories"
    bl_description = "Which colour attribute layer to select"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    collapse: BoolProperty(default=True, name="Collapse/Unfold Categories", description="Collapse/Unfold All Categories")  # type: ignore

    def execute(self, context):
        addon_find_modifiers_props = u.get_addon_find_modifier_props()

        # Access found objects from the UIList
        found_objects = addon_find_modifiers_props.objects_list.found_objects

        # Iterate all items
        for item in found_objects:
            # Only affect category headers
            if item.category_name:
                item.expanded = not self.collapse

        # Force UI Refresh
        context.area.tag_redraw()

        return {"FINISHED"}


# fmt: off
classes = [
    SimpleToolbox_OT_FindModifiersCategoryVisCollapse,
]
# fmt: on


def register():
    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
