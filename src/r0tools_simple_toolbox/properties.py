import bpy
from bpy.props import StringProperty  # type: ignore
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
)

from . import utils as u
from .const import INTERNAL_NAME
from .keymaps import draw_keymap_settings

# -------------------------------------------------------------------
#   ADDON PROPS
# -------------------------------------------------------------------
# Properties which are not stored in preferences


# ----- Custom Object Properties & Items -----
class R0PROP_UL_CustomPropertiesList(bpy.types.UIList):
    """UI List where each entry is a custom property belonging to at least 1 selected object"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        row = layout.row(align=True)
        if item.type == u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA:
            row.label(text="", icon="OBJECT_DATA")
        elif item.type == u.CUSTOM_PROPERTIES_TYPES.MESH_DATA:
            row.label(text="", icon="MESH_DATA")
        row.label(text=item.name)
        row.prop(item, "selected", text="")


class R0PROP_PG_CustomPropertyItem(bpy.types.PropertyGroup):
    """Property that represents an entry in the Custom Property UI List"""

    name: StringProperty()  # type: ignore
    selected: BoolProperty(default=False)  # type: ignore
    type: StringProperty(default=u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA)  # type: ignore


# ----- Object Sets & Object Items -----
class R0PROP_ObjectSetObjectItem(bpy.types.PropertyGroup):
    """Property representing a reference to an Object within an Object Set"""

    object: bpy.props.PointerProperty(type=bpy.types.Object)  # type: ignore


class R0PROP_ObjectSetEntryItem(bpy.types.PropertyGroup):
    """Property that represents an Object Set that contains a reference to a collection of objects added to the set"""

    name: bpy.props.StringProperty(name="Object Set Name", default="New Object Set")  # type: ignore
    objects: bpy.props.CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    count: bpy.props.IntProperty(name="Count", default=0)  # type: ignore

    def add_object(self, obj):
        if not any(o.object == obj for o in self.objects):
            new_object = self.objects.add()
            new_object.object = obj

            self.update_count()

    def remove_object(self, obj):
        for i, o in enumerate(self.objects):
            if o.object == obj:
                self.objects.remove(i)
                break
        self.update_count()

    def update_count(self):
        self.count = len(self.objects)
        if u.IS_DEBUG():
            print(f"[DEBUG] Updated count for Set '{self.name}': {self.count}")


class R0PROP_UL_ObjectSetsList(bpy.types.UIList):
    """UI List where each entry is an Object Set that itself contains references to Objects added to the set"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row()

            row.prop(item, "name", text="", emboss=False, icon="MESH_CUBE")

            # Display object count
            count_text = f"({item.count})"
            row.label(text=count_text, icon="OBJECT_DATAMODE")

            # Alternative display, needs some work
            # split = row.split(align=True)
            # split.alignment = 'RIGHT'
            # split.label(text=f"({item.count})", icon="OBJECT_DATAMODE")

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text=item.name)

    def invoke(self, context, event):
        # Handle double-click event
        if event.type == "LEFTMOUSE" and event.value == "DOUBLE_CLICK":
            # Trigger rename operator
            bpy.ops.r0tools.rename_object_set("INVOKE_DEFAULT")
            return {"HANDLED"}
        return {"PASS_THROUGH"}


# -------------------------------------------------------------------
#   ADDON PROPERTIES
# -------------------------------------------------------------------
class r0SimpleToolboxProps(bpy.types.PropertyGroup):
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

    show_uv_island_area_thresholds: BoolProperty(  # type: ignore
        name="UV Island Area Thresholds", default=False
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
        default=True,
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

    screen_size_pct_prop: FloatProperty(  # type: ignore
        name="Screen Size Percentage",
        default=0.0,
        min=0.0,
        max=100.0,
        subtype="PERCENTAGE",
    )

    polygon_threshold: FloatProperty(  # type: ignore
        name="Screen Size Threshold (%)",
        default=1,
        min=0.0,
        max=100.0,
        description="Highlight meshes smaller than this screen size percentage",
    )

    show_custom_property_list_prop: BoolProperty(  # type: ignore
        name="Delete Custom Properties",
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
    object_sets: CollectionProperty(type=R0PROP_ObjectSetEntryItem)  # type: ignore
    object_sets_index: IntProperty(default=0)  # type: ignore
    data_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    scene_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    objects_updated: BoolProperty(default=False)  # type: ignore

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


# -------------------------------------------------------------------
#   ADDON PREFS
# -------------------------------------------------------------------
class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = INTERNAL_NAME

    debug: BoolProperty(
        name="Debug", description="Set Debug State", default=False  # type: ignore
    )

    check_update_startup: BoolProperty(  # type: ignore
        name="Check Update on Startup",
        description="Flag to set whether to check for extension updates on startup or not",
        default=True,
    )

    experimental_features: BoolProperty(  # type: ignore
        name="Experimental Features",
        description="Enable experimental features",
        default=False,
    )

    dev_tools: BoolProperty(  # type: ignore
        name="Dev Tools",
        description="Enable Dev Tool features",
        default=False,
    )

    clear_sharp_axis_float_prop: FloatProperty(  # type: ignore
        name="Clear Sharp Axis Threshold",
        default=0.0,
        min=0.0,
        description="Threshold value for vertex/edge selection",
        update=lambda self, context: u.save_preferences(),
    )

    object_sets_modal_width: IntProperty(  # type: ignore
        name="Object Sets Modal Width", default=275, min=0, max=400
    )

    object_sets_list_rows: IntProperty(  # type: ignore
        name="Object Sets List Rows", default=6, min=1
    )

    custom_properties_list_rows: IntProperty(  # type: ignore
        name="Custom Properties List Rows", default=6, min=1
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        row = layout.row()
        row.prop(self, "debug", text="Debug Mode")

        row = layout.row()
        row.prop(self, "experimental_features", text="Experimental Features")

        row = layout.row()
        row.prop(self, "check_update_startup", text="Check update on startup")

        layout.prop(
            self, "clear_sharp_axis_float_prop", text="Clear Sharp Edges Threshold"
        )

        # Object Sets
        object_sets_settings_box = layout.box()
        row = object_sets_settings_box.row()
        row.label(text="Object Sets Settings")
        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_modal_width")
        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_list_rows")

        # Custom Properties
        custom_properties_settings_box = layout.box()
        row = custom_properties_settings_box.row()
        row.label(text="Custom Properties Settings")
        row = custom_properties_settings_box.row()
        row.prop(self, "custom_properties_list_rows")

        # Keymaps
        draw_keymap_settings(layout, self)

    def save_axis_threshold(self):
        addon_prefs = bpy.context.preferences.addons[INTERNAL_NAME].preferences
        addon_prefs.clear_sharp_axis_float_prop = self.clear_sharp_axis_float_prop
        # print(f"Saved Property: clear_sharp_axis_float_prop -> {self.clear_sharp_axis_float_prop}")


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------
classes = [
    R0PROP_UL_CustomPropertiesList,
    R0PROP_PG_CustomPropertyItem,
    R0PROP_ObjectSetObjectItem,
    R0PROP_ObjectSetEntryItem,
    R0PROP_UL_ObjectSetsList,
    AddonPreferences,
    r0SimpleToolboxProps,
]

depsgraph_handlers = [
    u.handler_update_data_scene_objects,
    u.handler_continuous_property_list_update,
    u.handler_cleanup_object_set_invalid_references,
]

load_post_handlers = [u.handler_cleanup_object_set_invalid_references]


def register():
    for cls in classes:
        print(f"[PROPERTIES] Registering {cls}")
        bpy.utils.register_class(cls)

    print("[PROPERTIES] Registering bpy.types.Scene.r0fl_toolbox_props")
    # Registering to Scene also has the side effect of saving properties on a per scene/file basis, which is nice!
    bpy.types.Scene.r0fl_toolbox_props = PointerProperty(type=r0SimpleToolboxProps)

    addon_prefs = u.get_addon_prefs()
    global DEBUG
    if addon_prefs.debug:
        DEBUG = True
        print(f"[PREFERENCES] Set Addon Debug to True")
    else:
        DEBUG = False
        print(f"[PREFERENCES] Set Addon Debug to False")

    for handler in depsgraph_handlers:
        if handler not in bpy.app.handlers.depsgraph_update_post:
            if u.IS_DEBUG():
                print(f"[DEBUG] Registering depsgraph handler {handler}")
            bpy.app.handlers.depsgraph_update_post.append(handler)

    for handler in load_post_handlers:
        if handler not in bpy.app.handlers.load_post:
            if u.IS_DEBUG():
                print(f"[DEBUG] Registering load_post handler {handler}")
            bpy.app.handlers.load_post.append(handler)


def unregister():
    for handler in depsgraph_handlers:
        try:
            if handler in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.remove(handler)
        except Exception as e:
            print(f"[ERROR] Error removing handler {handler}: {e}")
            u.context_error_debug(error=e)

    for handler in load_post_handlers:
        try:
            if handler in bpy.app.handlers.load_post:
                if u.IS_DEBUG():
                    print(f"[DEBUG] Unregistering load_post handler {handler}")
                bpy.app.handlers.load_post.remove(handler)
        except Exception as e:
            print(f"[ERROR] Error removing handler {handler}: {e}")
            u.context_error_debug(error=e)

    for cls in classes:
        bpy.utils.unregister_class(cls)

    print(f"[PROPERTIES] Unregistering bpy.types.Scene.r0fl_toolbox_props")
    del bpy.types.Scene.r0fl_toolbox_props
