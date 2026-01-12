import logging

import bpy
from bpy.props import (  # type: ignore
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from .. import utils as u

log = logging.getLogger(__name__)


class R0PROP_FindModifierListItem(bpy.types.PropertyGroup):
    """
    Represents a single item in the found objects UIList.
    """

    category_name: bpy.props.StringProperty(default="")  # type: ignore
    obj: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)  # type: ignore
    expanded: bpy.props.BoolProperty(name="Expand/Collapse", default=False)  # type: ignore


class R0PROP_PG_FindModifierListProperties(bpy.types.PropertyGroup):
    found_objects: bpy.props.CollectionProperty(type=R0PROP_FindModifierListItem)  # type: ignore
    active_index: IntProperty(default=0, description="Active Index")  # type: ignore


class R0PROP_UL_FindModifierObjectsList(bpy.types.UIList):
    """UI List populated by objects that contain the searched for modifiers"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from ..operators import (
            SimpleToolbox_OT_FindModifierSelectCategory,
            SimpleToolbox_OT_FindModifierSelectObject,
        )

        # Category header
        if item.category_name:
            row = layout.row(align=True)
            expand_icon = "TRIA_DOWN" if item.expanded else "TRIA_RIGHT"
            row.prop(item, "expanded", text="", icon=expand_icon, emboss=False)
            row.label(text=item.category_name)
            op = row.operator(
                SimpleToolbox_OT_FindModifierSelectCategory.bl_idname, text="", icon="RESTRICT_SELECT_OFF"
            )
            op.category_name = item.category_name

        # Object entry
        else:
            found_obj = item.obj
            if not found_obj:
                layout.label(text="<Object Not Found>", icon="ERROR")
                return

            # Indent the object row
            split = layout.split(factor=0.1)
            split.label(text="")

            row = split.row()
            op = row.operator(SimpleToolbox_OT_FindModifierSelectObject.bl_idname, text="", icon="RESTRICT_SELECT_OFF")
            op.object_name = found_obj.name
            row.prop(found_obj, "name", text="", emboss=False)

    def filter_items(self, context, data, propname):
        """Filter items to hide objects when their category is collapsed"""
        # Get the collection
        items = getattr(data, propname)

        filter_flags = []
        filter_new_order = []

        current_category_expanded = True

        for i, item in enumerate(items):
            if item.category_name:
                # Always show category headers
                filter_flags.append(self.bitflag_filter_item)
                current_category_expanded = item.expanded
            else:
                # Show objects only if their category is expanded
                if current_category_expanded:
                    filter_flags.append(self.bitflag_filter_item)
                else:
                    filter_flags.append(0)  # Hide this item

        return filter_flags, filter_new_order


class r0SimpleToolboxFindModifierProps(bpy.types.PropertyGroup):
    experimental_features: BoolProperty(
        name="Experimental Features",
        description="Toggle experimental features",
        default=False,
    )  # type: ignore
    objects_list: PointerProperty(type=R0PROP_PG_FindModifierListProperties)  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_FindModifierListItem,
    R0PROP_PG_FindModifierListProperties,
    R0PROP_UL_FindModifierObjectsList,
    r0SimpleToolboxFindModifierProps,
]


load_post_handlers = []


def register():
    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)

    log.debug(f"Register bpy.types.Scene.r0fl_toolbox_find_modifier_props")
    bpy.types.Scene.r0fl_toolbox_find_modifier_props = PointerProperty(
        type=r0SimpleToolboxFindModifierProps, name="r0fl Toolbox Find Modifier"
    )

    for handler in load_post_handlers:
        log.debug(f"Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        log.debug(f"Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    log.debug(f"Unregister bpy.types.Scene.r0fl_toolbox_find_modifier_props")
    del bpy.types.Scene.r0fl_toolbox_find_modifier_props
