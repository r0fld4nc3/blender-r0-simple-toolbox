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

from . import utils as u

_mod = "PROPERTIES"

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


#############################
### Find Modifier & Items ###
#############################
class R0PROP_FindModifierListItem(bpy.types.PropertyGroup):
    """
    Represents a single item in the found objects UIList.
    """

    category_name: bpy.props.StringProperty(default="")  # type: ignore
    obj: bpy.props.PointerProperty(name="Object", type=bpy.types.Object)  # type: ignore
    expanded: bpy.props.BoolProperty(name="Expand/Collapse", default=True)  # type: ignore


class R0PROP_PG_FindModifierListProperties(bpy.types.PropertyGroup):
    found_objects: bpy.props.CollectionProperty(type=R0PROP_FindModifierListItem)  # type: ignore
    active_index: IntProperty(default=0, description="Active Index")  # type: ignore


class R0PROP_UL_FindModifierObjectsList(bpy.types.UIList):
    """UI List populated by objects that contain the searched for modifiers"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from .operators import SimpleToolbox_OT_FindModifierSelectObject

        # Category header
        if item.category_name:
            row = layout.row()
            expand_icon = "MODIFIER_DATA" if item.expanded else "TRIA_RIGHT"
            row.prop(item, "expanded", text="", icon=expand_icon, emboss=False)
            row.label(text=item.category_name)
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


# ===================================================================
#   ADDON PROPERTIES
# ===================================================================
class r0SimpleToolboxProps(bpy.types.PropertyGroup):
    # =======================================================================
    # Categories

    cat_show_object_ops: BoolProperty(
        name="Show Object Ops", description="Show operations for Object context", default=True
    )  # type: ignore

    cat_show_mesh_ops: BoolProperty(
        name="Show Mesh Ops", description="Show operations for Mesh context", default=True
    )  # type: ignore

    cat_show_uv_ops: BoolProperty(
        name="Show UV Ops", description="Show operations for UV context", default=False
    )  # type: ignore

    cat_show_find_modifiers_ops: BoolProperty(
        name="Show Find Modifiers", description="Show operations for Finding Modifiers", default=True
    )  # type: ignore

    cat_show_object_sets_editor: BoolProperty(
        name="Show Object Sets Editor", description="Show Object Sets Editor", default=True
    )  # type: ignore

    cat_show_vertex_groups_editor: BoolProperty(
        name="Show Vertex Groups Editor", description="Show Vertex Groups Editor", default=False
    )  # type: ignore

    cat_show_custom_properties_editor: BoolProperty(
        name="Show Custom Properties Editor", description="Show Custom Properties Editor", default=False
    )  # type: ignore

    # =======================================================================

    show_dev_tools: BoolProperty(  # type: ignore
        name="Dev Tools",
        description="Show or hide the development options section",
        default=False,
    )

    show_object_ops: BoolProperty(  # type: ignore
        name="Object Ops",
        description="Show or hide the Object operators section",
        default=True,
    )

    show_mesh_ops: BoolProperty(  # type: ignore
        name="Mesh Ops",
        description="Show or hide the Mesh operators section",
        default=True,
    )

    show_uv_ops: BoolProperty(  # type: ignore
        name="UV Ops",
        description="Show or hide the UV operators section",
        default=False,
    )

    show_experimental_features: BoolProperty(  # type: ignore
        name="Experimental",
        description="Show or hide the Experimental operators section",
        default=False,
    )

    show_uv_island_area_thresholds: BoolProperty(name="UV Island Area Thresholds", default=False)  # type: ignore

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

    show_custom_property_list_prop: BoolProperty(  # type: ignore
        name="Custom Properties",
        description="List Custom Properties",
        default=False,
    )

    custom_property_list: CollectionProperty(type=R0PROP_PG_CustomPropertyItem)  # type: ignore
    custom_property_list_index: IntProperty(default=0)  # type: ignore
    last_object_selection: StringProperty(  # type: ignore
        name="Last Object Selection",
        description="Comma-separated names of last selected objects",
        default="",
    )

    show_object_sets: BoolProperty(  # type: ignore
        name="Object Sets",
        description="Manage different object selections via an Object Set editor",
        default=False,
    )

    show_vertex_groups: BoolProperty(  # type: ignore
        name="Vertex Groups", description="Manage Vertex Groups of selected objects", default=False
    )

    show_find_modifier_search: BoolProperty(  # type: ignore
        name="Find Modifier(s)",
        description="Show Find Object with Modifiers Controls",
        default=False,
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
    from .addon_properties.object_sets_props import R0PROP_PG_ObjectSetEntryItem
    from .addon_properties.vertex_groups_props import R0PROP_PG_VertexGroupPropertyItem

    object_sets: CollectionProperty(type=R0PROP_PG_ObjectSetEntryItem)  # type: ignore


class r0SimpleToolboxFindModifierProps(bpy.types.PropertyGroup):
    objects_list: PointerProperty(type=R0PROP_PG_FindModifierListProperties)  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_UL_CustomPropertiesList,
    R0PROP_PG_CustomPropertyItem,
    R0PROP_FindModifierListItem,
    R0PROP_PG_FindModifierListProperties,
    R0PROP_UL_FindModifierObjectsList,
    r0SimpleToolboxProps,
    r0SimpleToolboxFindModifierProps,
]


load_post_handlers = []


def register():
    for cls in classes:
        print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_props")
    # Registering to Scene also has the side effect of saving properties on a per scene/file basis, which is nice!
    bpy.types.Scene.r0fl_toolbox_props = PointerProperty(type=r0SimpleToolboxProps)

    print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_find_modifier_props")
    bpy.types.Scene.r0fl_toolbox_find_modifier_props = PointerProperty(type=r0SimpleToolboxFindModifierProps)

    for handler in load_post_handlers:
        print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_props")
    del bpy.types.Scene.r0fl_toolbox_props

    print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_find_modifier_props")
    del bpy.types.Scene.r0fl_toolbox_find_modifier_props
