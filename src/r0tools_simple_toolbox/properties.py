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
from .defines import INTERNAL_NAME
from .keymaps import draw_keymap_settings

# ===================================================================
#   ADDON PROPS
# ===================================================================
# Properties which are not stored in preferences


# ----- Custom Object Properties & Items -----
class R0PROP_UL_CustomPropertiesList(bpy.types.UIList):
    """UI List where each entry is a custom property belonging to at least 1 selected object"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
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


# ===== Object Sets & Object Items =====
class R0PROP_ObjectSetObjectItem(bpy.types.PropertyGroup):
    """Property representing a reference to an Object within an Object Set"""

    object: bpy.props.PointerProperty(type=bpy.types.Object)  # type: ignore


class R0PROP_ObjectSetEntryItem(bpy.types.PropertyGroup):
    """Property that represents an Object Set that contains a reference to a collection of objects added to the set"""

    def update_object_set_colour(self, dummy):
        addon_prefs = u.get_addon_prefs()
        allow_override = addon_prefs.object_sets_colour_allow_override

        for item in self.objects:
            obj = item.object
            if obj is None:
                continue

            obj.color = self.set_colour
            # Check in contained in set
            containing_sets = self.check_object_in_sets(obj)
            if not containing_sets:  # Object not in an Object Set
                if u.IS_DEBUG():
                    print(f"[DEBUG] Object {obj.name} not present in any Object Set.")
                obj.color = self.set_colour
            elif containing_sets:
                if u.IS_DEBUG():
                    print(
                        f"[DEBUG] Object {obj.name} contained in {len(containing_sets)} Object Sets. Allow Colour Override is {allow_override}"
                    )
                if not allow_override:
                    obj.color = containing_sets[0].set_colour
                else:
                    # Only allow colour override if flag is set.
                    obj.color = self.set_colour

    def set_object_set_colour(self, colour: list):
        """
        Set colour of Object Set.
        """

        # update=func passes context as an argument but we want to
        # pass a list of floats. So in order to workaround having
        # to create a new method to support this, let's just
        # enfore that the type(colour) must be in accepted types
        if type(colour) in [type(self.set_colour), list, tuple]:
            self.set_colour = colour

        for item in self.objects:
            obj = item.object
            if obj is None:
                continue

            obj.color = self.set_colour

    name: bpy.props.StringProperty(name="Object Set Name", default="New Object Set")  # type: ignore
    separator: bpy.props.BoolProperty(default=False)  # type: ignore
    _default_separator_name = "-" * 16

    objects: bpy.props.CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    count: bpy.props.IntProperty(name="Count", default=0)  # type: ignore
    set_colour: bpy.props.FloatVectorProperty(  # type: ignore
        name="Set Object Set Colour",
        subtype="COLOR",
        size=4,  # RGBA
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=set_object_set_colour,  # This passes `Context` as an argument....
    )

    def assign_object(self, obj):
        if self.separator:
            return

        if not any(o.object == obj for o in self.objects):
            new_object = self.objects.add()
            new_object.object = obj

            self.update_count()

    def remove_object(self, obj):
        addon_prefs = u.get_addon_prefs()
        allow_override = addon_prefs.object_sets_colour_allow_override

        if self.separator:
            return

        for i, o in enumerate(self.objects):
            # What if it's an unknown reference?
            try:
                if o.object and o.object.as_pointer != 0 and o.object == obj or o.object.as_pointer == 0:
                    self.objects.remove(i)
                    break
            except Exception as e:
                print(f"[ERROR] [PROPERTIES] {e}")

        # Check if object still exists:
        try:
            valid = u.is_valid_object_global(obj)
        except Exception as e:
            print(f"[ERROR] [PROPERTIES] Is valid object global check error: {e}")
            self.update_count()
            return

        if valid:
            # Check if object not in other sets
            containing_sets = self.check_object_in_sets(obj)
            if not containing_sets:
                obj.color = (1.0, 1.0, 1.0, 1.0)
            else:
                # Update the object to another set's colour
                if allow_override:
                    obj.color = containing_sets[-1].set_colour
                else:
                    obj.color = containing_sets[0].set_colour

        self.update_count()

    def check_object_in_sets(self, obj) -> list:
        """
        Checks if an object is present in more Object Sets. If so
        return a list of references to each Object Set containing the object

        :return: `list` of `Object Sets`
        """
        addon_props = u.get_addon_props()
        containing_sets = []

        for obj_set in addon_props.object_sets:
            if obj_set.separator:
                continue
            for obj_item in obj_set.objects:
                if obj_item.object == obj:
                    if obj_set not in containing_sets:
                        containing_sets.append(obj_set)

        return containing_sets

    def update_count(self):
        if self.separator:
            return

        self.count = len(self.objects)
        if u.IS_DEBUG():
            print(f"[DEBUG] Updated count for Set '{self.name}': {self.count}")

        self.update_object_set_colour(self)


class R0PROP_UL_ObjectSetsList(bpy.types.UIList):
    """UI List where each entry is an Object Set that itself contains references to Objects added to the set"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        addon_prefs = u.get_addon_prefs()

        # Check if the item to insert is a separator
        if item.separator:
            # Draw separator
            row = layout.row()
            row.enabled = False
            row.alignment = "CENTER"
            row.label(text=item.name)
            return

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)

            # Configure accordingly for object sets colour
            if addon_prefs.object_sets_use_colour:
                scale_x = 0.8  # Scales extending the right side to the right
                scale_y = 0.8  # Scales extending the bottom down
                row.separator(factor=0.8)  # Pushes things to the right
                object_set_colour_row = row.row(align=True)
                object_set_colour_row.alignment = "LEFT"
                col = object_set_colour_row.column()
                # col.label(text="", icon="MESH_CUBE")
                col = object_set_colour_row.column()
                col.ui_units_x = scale_x
                col.separator(factor=0.3)  # Pushes things down
                col.scale_y = scale_y
                col.prop(item, "set_colour", text="")
                # Right side padding. Breathing room in case other widget is on the right side
                row.separator(factor=0.5)

            # Info Row
            info_row = row.row(align=True)

            # Select Set
            col_select_set = info_row.row(align=True)
            """
            OMG this is exciting. So we store a reference to the Operator
            and then we immediately assign it a property defined in the Operator class
            `set_index`. By doing this, we can store which set the button belongs to
            and can select the objects of the given Object Set at a specific row/index
            without having to first select the row!!! Amazing!
            """
            op = col_select_set.operator(
                "r0tools.select_object_set",
                text="",
                icon="RESTRICT_SELECT_OFF",
            )
            # Set the property before adding to layout
            op.set_index = index
            # Add spacing after the operation is complete
            col_select_set.separator(factor=0.5)

            """
            if (
                not addon_prefs.object_sets_use_colour
                or not addon_prefs.experimental_features
            ):
                icon_row = info_row.row(align=True)
                icon_row.label(text="", icon="MESH_CUBE")
            """
            # Name
            col_name = info_row.row(align=True)
            col_name.prop(item, "name", text="", emboss=False, icon="NONE")

            # Object Count
            col_item_count = info_row.row(align=True)
            col_item_count.alignment = "RIGHT"
            col_item_count.label(text=f"({item.count})", icon="NONE")

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text=item.name)


# ===================================================================
#   ADDON PROPERTIES
# ===================================================================
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
    object_sets: CollectionProperty(type=R0PROP_ObjectSetEntryItem)  # type: ignore
    object_sets_index: IntProperty(default=0)  # type: ignore
    # data_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    # scene_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
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


# ===================================================================
#   ADDON PREFS
# ===================================================================
class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = INTERNAL_NAME

    debug: BoolProperty(name="Debug", description="Set Debug State", default=False)  # type: ignore

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

    object_sets_use_colour: BoolProperty(  # type: ignore
        name="Object Sets Use Colour",
        description="Objects Sets are given a colour. This colour is set as the Object's Colour depending on which set it is in and the viewport wire display is set to use Object as the display type",
        default=True,
    )

    object_sets_colour_allow_override: BoolProperty(  # type: ignore
        name="Allow Colour Override",
        description="Allow colour override for objects that area already present in Object Sets and are added or modified in other sets. When disallowed, the object will (hopefully) only retain the colour of the first Object Set is contained in.\nWhen allowed, the object will change colours freely depending on the last modified set, given the object is contained within.",
        default=False,
    )

    object_sets_default_colour: FloatVectorProperty(  # type: ignore
        name="Object Sets Default Colour",
        subtype="COLOR",
        size=4,  # RGBA
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )

    object_sets_modal_width: IntProperty(name="Object Sets Modal Width", default=300, min=0, max=400)  # type: ignore

    object_sets_list_rows: IntProperty(name="Object Sets List Rows", default=6, min=1)  # type: ignore

    custom_properties_list_rows: IntProperty(name="Custom Properties List Rows", default=6, min=1)  # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        row = layout.row()
        row.prop(self, "debug", text="Debug Mode")

        row = layout.row()
        row.prop(self, "experimental_features", text="Experimental Features")

        row = layout.row()
        row.prop(self, "check_update_startup", text="Check update on startup")

        layout.prop(self, "clear_sharp_axis_float_prop", text="Clear Sharp Edges Threshold")

        # Object Sets
        object_sets_settings_box = layout.box()
        row = object_sets_settings_box.row()
        row.label(text="Object Sets Settings")
        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_modal_width")
        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_list_rows")
        # Object Sets Use Colour
        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_use_colour")

        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_colour_allow_override")

        if self.object_sets_use_colour:
            row = object_sets_settings_box.row()
            row.prop(self, "object_sets_default_colour", text="Default Colour")

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


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_UL_CustomPropertiesList,
    R0PROP_PG_CustomPropertyItem,
    R0PROP_ObjectSetObjectItem,
    R0PROP_ObjectSetEntryItem,
    R0PROP_UL_ObjectSetsList,
    AddonPreferences,
    r0SimpleToolboxProps,
]


def register():
    for cls in classes:
        print(f"[PROPERTIES] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    print("[PROPERTIES] Register bpy.types.Scene.r0fl_toolbox_props")
    # Registering to Scene also has the side effect of saving properties on a per scene/file basis, which is nice!
    bpy.types.Scene.r0fl_toolbox_props = PointerProperty(type=r0SimpleToolboxProps)

    addon_prefs = u.get_addon_prefs()
    global DEBUG
    if addon_prefs.debug:
        DEBUG = True
        print(f"[PROPERTIES] Set Addon Debug to True")
    else:
        DEBUG = False
        print(f"[PROPERTIES] Set Addon Debug to False")


def unregister():
    for cls in classes:
        print(f"[PROPERTIES] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    print(f"[PROPERTIES] Unregister bpy.types.Scene.r0fl_toolbox_props")
    del bpy.types.Scene.r0fl_toolbox_props
