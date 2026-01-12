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

# ===================================================================
#   ADDON PROPERTIES
# ===================================================================


##############################################
###### Custom Object Properties & Items ######
##############################################
class R0PROP_UL_CustomPropertiesList(bpy.types.UIList):
    """UI List where each entry is a custom property belonging to at least 1 selected object"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        if item.type == u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA:
            row.label(text="", icon="OBJECT_DATA")
        elif item.type == u.CUSTOM_PROPERTIES_TYPES.MESH_DATA:
            row.label(text="", icon="MESH_DATA")
        row.prop(item, "selected", text="")
        row.label(text=item.name)


class R0PROP_PG_CustomPropertyItem(bpy.types.PropertyGroup):
    """Property that represents an entry in the Custom Property UI List"""

    name: StringProperty()  # type: ignore
    selected: BoolProperty(default=False)  # type: ignore
    type: StringProperty(default=u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA)  # type: ignore


#######################################
###### Object Attributes & Items ######
#######################################
class R0PROP_UL_ObjectAttributesList(bpy.types.UIList):
    """UI List where each entry is an Object Attribute belonging to at least 1 selected object"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "selected", text="")
        row.label(text=item.name)


class R0PROP_PG_ObjectAttributeItem(bpy.types.PropertyGroup):
    """Property that represents an entry in the Attributes UI List"""

    name: StringProperty()  # type: ignore
    selected: BoolProperty(default=False)  # type: ignore


# ===================================================================
#   ADDON PROPERTIES
# ===================================================================
class r0SimpleToolboxProps(bpy.types.PropertyGroup):
    # =======================================================================
    # Categories

    cat_show_object_ops: BoolProperty(
        name="Toggle Object Ops", description="Toggle operations for Object context", default=False
    )  # type: ignore

    cat_show_mesh_ops: BoolProperty(
        name="Toggle Mesh Ops", description="Toggle operations for Mesh context", default=False
    )  # type: ignore

    cat_show_uv_ops: BoolProperty(
        name="Toggle UV Ops", description="Toggle operations for UV context", default=False
    )  # type: ignore

    cat_show_find_modifiers_ops: BoolProperty(
        name="Toggle Find Modifiers", description="Toggle operations for Finding Modifiers", default=False
    )  # type: ignore

    cat_show_object_sets_editor: BoolProperty(
        name="Toggle Object Sets Panel", description="Toggle Object Sets Editor Panel", default=False
    )  # type: ignore

    cat_show_vertex_groups_editor: BoolProperty(
        name="Toggle Vertex Groups Panel", description="Toggle Vertex Groups Editor Panel", default=False
    )  # type: ignore

    cat_show_edge_data_panel: BoolProperty(
        name="Toggle Edge Data Panel", description="Toggle Edge Data Panel", default=False
    )  # type: ignore

    cat_show_quick_export_panel: BoolProperty(
        name="Toggle Quick Export Panel", description="Toggle Quick Export Panel", default=False
    )  # type: ignore

    cat_show_custom_properties_editor: BoolProperty(
        name="Toggle Custom Properties Editor", description="Toggle Custom Properties Editor", default=False
    )  # type: ignore

    # =======================================================================
    # Category panels
    panelvis_dev_tools: BoolProperty(
        name="Dev Tools", description="Toggle visibility state for panel", default=False
    )  # type: ignore

    panelvis_object_ops: BoolProperty(
        name="Object Ops", description="Toggle visibility state for panel", default=False
    )  # type: ignore
    panelvis_mesh_ops: BoolProperty(
        name="Mesh Ops", description="Toggle visibility state for panel", default=False
    )  # type: ignore
    panelvis_uv_ops: BoolProperty(
        name="UV Ops", description="Toggle visibility state for panel", default=False
    )  # type: ignore
    panelvis_find_modifier_ops: BoolProperty(
        name="Find Modifier", description="Toggle visibility state for panel", default=False
    )  # type: ignore
    panelvis_object_sets_ops: BoolProperty(
        name="Object Sets", description="Toggle visibility state for panel", default=False
    )  # type: ignore
    panelvis_vertex_groups_ops: BoolProperty(
        name="Vertex Groups", description="Toggle visibility state for panel", default=False
    )  # type: ignore
    panelvis_custom_properties_ops: BoolProperty(
        name="Custom Properties", description="Toggle visibility state for panel", default=False
    )  # type: ignore

    panelvis_object_attributes: BoolProperty(
        name="Object Attributes", description="Toggle visibility state for panel", default=False
    )  # type: ignore

    # =======================================================================

    show_experimental_features: BoolProperty(  # type: ignore
        name="Experimental",
        description="Show or hide the Experimental operators section",
        default=False,
    )

    uvisland_sizecheck_arearelative: FloatProperty(  # type: ignore
        name="Relative Area Size",
        description="Area Factor occupied by the UV Island relative to 0 - 1 Space",
        default=0.00001,
        min=0.0,
        max=1.0,
    )

    use_uvisland_sizecheck_arearelative: BoolProperty(  # type: ignore
        name="Use Relative Area Size",
        description="Area Factor occupied by the UV Island relative to 0 - 1 Space",
        default=False,
    )

    uvisland_sizecheck_area_pixelcoverage: FloatProperty(  # type: ignore
        name="Area Pixel Coverage",
        description="Area Squared (px²) of UV Island",
        default=80.0,
        min=0.0,
    )

    use_uvisland_sizecheck_area_pixelcoverage: BoolProperty(  # type: ignore
        name="Use Area Pixel Coverage",
        description="Use Area Squared (px²) of UV Island",
        default=False,
    )

    uvisland_sizecheck_area_pixelpercentage: FloatProperty(  # type: ignore
        name="Area Pixel Percentage",
        description="Percentage Area occupied by the UV Island",
        default=0.001,
        min=0.0,
        max=100.0,
    )

    use_uvisland_sizecheck_area_pixelpercentage: BoolProperty(  # type: ignore
        name="Use Area Pixel Percentage",
        description="Percentage Area occupied by the UV Island",
        default=True,
    )

    show_clear_sharps_on_axis: BoolProperty(  # type: ignore
        name="Clear Sharp Edges on Axis",
        description="Show or hide the Clear Sharps on Axis operator",
        default=False,
    )

    show_ext_ops: BoolProperty(  # type: ignore
        name="External Ops",
        description="Show or hide the External operators section",
        default=False,
    )

    reload_modules_prop: StringProperty(  # type: ignore
        name="Module(s)", description="Command-separated list of module names"
    )

    polygon_threshold: FloatProperty(  # type: ignore
        name="Screen Size Threshold (%)",
        default=1,
        min=0.0,
        max=100.0,
        description="Highlight meshes smaller than this screen size percentage",
    )

    custom_property_list: CollectionProperty(type=R0PROP_PG_CustomPropertyItem)  # type: ignore
    custom_property_list_index: IntProperty(default=0)  # type: ignore

    object_attributes_list: CollectionProperty(type=R0PROP_PG_ObjectAttributeItem)  # type: ignore
    object_attributes_list_index: IntProperty(default=0)  # type: ignore

    last_object_selection: StringProperty(  # type: ignore
        name="Last Object Selection",
        description="Comma-separated names of last selected objects",
        default="",
    )

    find_modifier_search_text: StringProperty(  # type: ignore
        name="Modifier Type/Name",
        description='Name or Type of Modifier to find.\nTo search for a mix of name and type and/or multiple criteria, use a comma-separated string, ex.: "!!, weld, nodes"\nNote: Case Insensitive',
        default="",
    )

    uv_sizes_options = [
        ("64", "64", "Pixels per kilometer", 0),
        ("128", "128", "Pixels per kilometer", 1),
        ("256", "256", "Pixels per meter", 2),
        ("512", "512", "Pixels per centimeter", 3),
        ("1024", "1024", "Pixels per millimeter", 4),
        ("2048", "2048", "Pixels per micrometer", 5),
        ("4096", "4096", "Pixels per mil", 6),
        ("8192", "8192", "Pixels per mil", 7),
    ]

    uv_size_x: EnumProperty(  # type: ignore
        name="uv_size_x",
        items=uv_sizes_options,
        description="Size of UV Map X",
        default="4096",
        update=lambda self, context: u.save_preferences(),
    )

    uv_size_y: EnumProperty(  # type: ignore
        name="uv_size_x",
        items=uv_sizes_options,
        description="Size of UV Map Y",
        default="4096",
        update=lambda self, context: u.save_preferences(),
    )

    ##############
    ### LEGACY ###
    ##############
    from .object_sets_props import R0PROP_PG_ObjectSetEntryItem
    from .vertex_groups_props import R0PROP_PG_VertexGroupPropertyItem

    object_sets: CollectionProperty(type=R0PROP_PG_ObjectSetEntryItem)  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_UL_CustomPropertiesList,
    R0PROP_PG_CustomPropertyItem,
    R0PROP_UL_ObjectAttributesList,
    R0PROP_PG_ObjectAttributeItem,
    r0SimpleToolboxProps,
]


load_post_handlers = []


def register():
    for cls in classes:
        if u.is_debug():
            log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if u.is_debug():
        log.debug(f"Register bpy.types.Scene.r0fl_toolbox_props")
    # Registering to Scene also has the side effect of saving properties on a per scene/file basis, which is nice!
    bpy.types.Scene.r0fl_toolbox_props = PointerProperty(type=r0SimpleToolboxProps, name="r0fl Toolbox")

    for handler in load_post_handlers:
        if u.is_debug():
            log.debug(f"Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        if u.is_debug():
            log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        if u.is_debug():
            log.debug(f"Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    if u.is_debug():
        log.debug(f"Unregister bpy.types.Scene.r0fl_toolbox_props")
    del bpy.types.Scene.r0fl_toolbox_props
