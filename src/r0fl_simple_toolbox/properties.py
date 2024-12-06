import bpy
from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       CollectionProperty,
                       PointerProperty,
                       )

from .const import INTERNAL_NAME

# ============ ADDON PROPS =============
# Properties which are not stored in preferences
class RPROP_UL_custom_property_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "selected", text="")
        row.label(text=item.name)


class CustomPropertyItem(bpy.types.PropertyGroup):
    name: StringProperty()
    selected: BoolProperty(default=False)


class r0flToolboxProps(bpy.types.PropertyGroup):
    show_dev_tools: BoolProperty(
        name="Dev Tools",
        description="Show or hide the development options section",
        default=False
    )

    show_object_ops: BoolProperty(
        name="Object Ops",
        description="Show or hide the Object operators section",
        default=False
    )
    
    show_mesh_ops: BoolProperty(
        name="Mesh Ops",
        description="Show or hide the Mesh operators section",
        default=False
    )

    show_ext_ops: BoolProperty(
        name="External Ops",
        description="Show or hide the External operators section",
        default=False
    )

    reload_modules_prop: StringProperty(
        name="Module(s)",
        description="Command-separated list of module names"
    )

    screen_size_pct_prop: FloatProperty(
        name="Screen Size Percentage",
        default=0.0,
        min=0.0,
        max=100.0,
        subtype="PERCENTAGE"
    )

    polygon_threshold: FloatProperty(
        name="Screen Size Threshold (%)",
        default=1,
        min=0.0,
        max=100.0,
        description="Highlight meshes smaller than this screen size percentage"
    )

    show_custom_property_list_prop: BoolProperty(
        name="Delete Custom Properties",
        description="List Custom Properties",
        default=False
    )

    custom_property_list: CollectionProperty(type=CustomPropertyItem)
    custom_property_list_index: IntProperty(default=0)
    last_object_selection: StringProperty(
        name="Last Object Selection",
        description="Comma-separated names of last selected objects",
        default=''
    )


# ============ ADDON PREFS =============
class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = INTERNAL_NAME

    experimental_features: BoolProperty(
        name="Experimental Features",
        description="Enable experimental features",
        default=False
    )
    
    clear_sharp_axis_float_prop: FloatProperty(
        name="Clear Sharp Axis Threshold",
        default=0.0,
        min=0.0,
        description="Threshold value for vertex/edge selection",
        update=lambda self, context: save_preferences()
    )
    
    zenuv_td_prop: FloatProperty(
        name="ZenUV Texel Density",
        default=10.0,
        min=0.0,
        description="Texel Density value to apply to meshes",
        update=lambda self, context: save_preferences()
    )
    
    zenuv_unit_options = zenuv_unit_options = [
        ('PX_KM', "px/km", "Pixels per kilometer", 0),
        ('PX_M', "px/m", "Pixels per meter", 1),
        ('PX_CM', "px/cm", "Pixels per centimeter", 2),
        ('PX_MM', "px/mm", "Pixels per millimeter", 3),
        ('PX_UM', "px/um", "Pixels per micrometer", 4),
        ('PX_MIL', "px/mil", "Pixels per mil", 5),
        ('PX_FT', "px/ft", "Pixels per foot", 6),
        ('PX_IN', "px/in", "Pixels per inch", 7),
        ('PX_TH', "px/th", "Pixels per thou", 8)
    ]
    zenuv_td_unit_prop: EnumProperty(
        name="zenuv_td_unit_prop",
        items=zenuv_unit_options,
        description="Texel Density value to apply to meshes",
        default='PX_CM',
        update=lambda self, context: save_preferences()
    )
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        row = layout.row()
        row.prop(self, "experimental_features", text="Experimental Features")

        layout.prop(self, "clear_sharp_axis_float_prop", text="Clear Sharp Edges Threshold")
        
        # Box for texel density settings
        td_box = layout.box()
        td_box.label(text="Texel Density Settings")
        
        # Add the dropdown and value field in separate rows
        row = td_box.row()
        row.prop(self, "zenuv_td_prop")
        
        row = td_box.row()
        row.prop(self, "zenuv_td_unit_prop")
        
    def save_axis_threshold(self):
        addon_prefs = bpy.context.preferences.addons["r0fl_simple_toolbox"].preferences
        addon_prefs.clear_sharp_axis_float_prop = self.clear_sharp_axis_float_prop
        # print(f"Saved Property: clear_sharp_axis_float_prop -> {self.clear_sharp_axis_float_prop}")


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = [
    RPROP_UL_custom_property_list,
    CustomPropertyItem,
    AddonPreferences,
    r0flToolboxProps,
]

def register():
    for cls in classes:
        print(f"[PROPERTIES] Registering {cls}")
        bpy.utils.register_class(cls)
    
    print("[PROPERTIES] Registering bpy.types.Scene.r0fl_toolbox_props")
    bpy.types.Scene.r0fl_toolbox_props = PointerProperty(type=r0flToolboxProps)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.r0fl_toolbox_props
