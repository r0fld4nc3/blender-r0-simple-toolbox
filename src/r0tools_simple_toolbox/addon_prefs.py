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
from .defines import INTERNAL_NAME
from .keymaps import draw_keymap_settings

_mod = "PREFERENCES"


class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = INTERNAL_NAME

    debug: BoolProperty(name="Debug", description="Set Debug State", default=False)  # type: ignore

    log_output: BoolProperty(name="Log", description="Whehter to produce regular Log output", default=False)  # type: ignore

    lock_states_avoided: IntProperty(
        name="Avoided Locks",
        description="Silly counter to log how many crashes were avoided by forbidden ID context writes",
        default=0,
    )  # type: ignore

    check_update_startup: BoolProperty(
        name="Check Update on Startup",
        description="Flag to set whether to check for extension updates on startup or not",
        default=True,
    )  # type: ignore

    experimental_features: BoolProperty(
        name="Experimental Features",
        description="Enable experimental features",
        default=False,
    )  # type: ignore

    dev_tools: BoolProperty(
        name="Dev Tools",
        description="Enable Dev Tool features",
        default=False,
    )  # type: ignore

    clear_sharp_axis_float_prop: FloatProperty(
        name="Clear Sharp Axis Threshold",
        default=0.0,
        min=0.0,
        description="Threshold value for vertex/edge selection",
        update=lambda self, context: u.save_preferences(),
    )  # type: ignore

    object_sets_use_colour: BoolProperty(
        name="Object Sets Use Colour",
        description="Objects Sets are assigned a colour. Each object within the set is also assigned the colour of the Object Set it is contained in.\nTo view the objects with their assigned colour, change the Viewport Shading either to 'Wire Shading > Object' and/or 'Color > Object'.\nWhen an object is contained in multiple Object Sets, depending on the setting that allows the override, it will display in either the colour of the first Object Set it is found in, or the last",
        default=True,
    )  # type: ignore

    object_sets_colour_allow_override: BoolProperty(
        name="Allow Colour Override",
        description="Allow colour override for objects that area already present in Object Sets and are added or modified in other sets. When disallowed, the object will (hopefully) only retain the colour of the first Object Set is contained in.\nWhen allowed, the object will change colours freely depending on the last modified set, given the object is contained within.",
        default=False,
    )  # type: ignore

    object_sets_default_colour: FloatVectorProperty(
        name="Object Sets Default Colour",
        subtype="COLOR",
        size=4,  # RGBA
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )  # type: ignore

    object_sets_modal_width: IntProperty(name="Object Sets Modal Width", default=300, min=0, max=400)  # type: ignore

    object_sets_list_rows: IntProperty(name="Object Sets List Rows", default=6, min=1)  # type: ignore

    custom_properties_list_rows: IntProperty(name="Custom Properties List Rows", default=6, min=1)  # type: ignore

    vertex_groups_list_rows: IntProperty(name="Vertex Groups List Rows", default=8, min=1)  # type: ignore

    #######################
    ### Edge Data Reset ###
    #######################
    edge_reset_sharp: BoolProperty(name="Reset Edge Sharpness", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_seam: BoolProperty(name="Reset Edge Seam", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_crease: BoolProperty(name="Reset Edge Crease", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_bevel_weight: BoolProperty(name="Reset Edge Bevel Weight", description="Set whether to always reset this component", default=True)  # type: ignore

    edge_data_bweight_presets_alt_view: BoolProperty(name="Toggle Alternative View", description="Toggle between a set of buttons configured by arranged presets or a simple set of buttons", default=True)  # type: ignore

    keymap_toggle_wire: StringProperty(name="Toggle Wire Display Mode Key", default="FOUR")  # type: ignore

    keymap_object_sets_modal: StringProperty(name="Object Sets Modal Key", default="ONE")  # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        lock_states_avoided_row = layout.row()
        lock_states_avoided_row.label(text=f"Lock States Avoided: {self.lock_states_avoided}")

        row = layout.row()
        row.prop(self, "debug", text="Debug Mode")

        row = layout.row()
        row.prop(self, "log_output", text="Log Output")

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
        # u.LOG(f"[INFO] [{_mod}] Saved Property: clear_sharp_axis_float_prop -> {self.clear_sharp_axis_float_prop}")


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    AddonPreferences,
]


def register():
    for cls in classes:
        # print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    addon_prefs = u.get_addon_prefs()
    global DEBUG
    if addon_prefs.debug:
        DEBUG = True
    else:
        DEBUG = False


def unregister():
    for cls in classes:
        # print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
