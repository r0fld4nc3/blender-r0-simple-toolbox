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

from . import utils as u
from .defines import INTERNAL_NAME
from .keymaps import draw_keymap_settings

log = logging.getLogger(__name__)


class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = INTERNAL_NAME

    debug: BoolProperty(name="Debug", description="Set Debug State", default=False)  # type: ignore

    log_output: BoolProperty(name="Log", description="Whehter to produce regular Log output", default=False)  # type: ignore

    check_update_startup: BoolProperty(
        name="Check Update on Startup",
        description="Flag to set whether to check for extension updates on startup or not",
        default=True,
    )  # type: ignore

    experimental_features: BoolProperty(
        name="Experimental Features",
        description="Toggle experimental features",
        default=False,
    )  # type: ignore

    dev_tools: BoolProperty(
        name="Dev Tools",
        description="Toggle Dev Tool features",
        default=False,
    )  # type: ignore

    clear_sharp_axis_float_prop: FloatProperty(
        name="Clear Sharp Axis Threshold",
        default=0.0,
        min=0.0,
        description="Threshold value for vertex/edge selection",
        update=lambda self, context: u.save_preferences(),
    )  # type: ignore

    OPERATOR_COLUMN_SIZE_X = 0.7

    #########################
    ### CUSTOM PROPERTIES ###
    #########################
    custom_properties_list_rows: IntProperty(name="Custom Properties List Rows", default=6, min=1)  # type: ignore

    #########################
    ### OBJECT ATTRIBUTES ###
    #########################
    object_attributes_list_rows: IntProperty(name="Object Attributes List Rows", default=6, min=1)  # type: ignore

    ###################
    ### OBJECT SETS ###
    ###################
    object_sets_default_colour: FloatVectorProperty(
        name="Object Sets Default Colour",
        subtype="COLOR",
        size=4,  # RGBA
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
    )  # type: ignore

    #######################
    ### EDGE DATA RESET ###
    #######################
    edge_reset_sharp: BoolProperty(name="Reset Edge Sharpness", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_seam: BoolProperty(name="Reset Edge Seam", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_crease: BoolProperty(name="Reset Edge Crease", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_bevel_weight: BoolProperty(name="Reset Edge Bevel Weight", description="Set whether to always reset this component", default=True)  # type: ignore

    edge_data_bweight_presets_alt_view: BoolProperty(name="Toggle Alternative View", description="Toggle between a set of buttons configured by arranged presets or a simple set of buttons", default=True)  # type: ignore

    keymap_toggle_wire: StringProperty(name="Toggle Wire Display Mode Key", default="FOUR")  # type: ignore

    keymap_object_sets_modal: StringProperty(name="Object Sets Modal Key", default="ONE")  # type: ignore

    ###################
    ### EXPORT SETS ###
    ###################
    from .addon_properties.export_props import r0SimpleToolbox_PG_FBXExportSettings

    export_settings_global_fbx: PointerProperty(type=r0SimpleToolbox_PG_FBXExportSettings, name="FBX Export Settings", description="Global FBX Exporter Settings")  # type: ignore

    #########################
    ### OBJECT ATTRIBUTES ###
    #########################
    object_attributes_to_keep: StringProperty(
        name="Attributes To Keep",
        description="Comma-separated list of attribute names to never delete",
        default="sharp_edge, uv_seam, custom_normal, material_index, UVMap",
    )  # type: ignore

    def draw(self, context):
        addon_object_sets_props = u.get_addon_object_sets_props()

        layout = self.layout
        layout.use_property_split = False

        row = layout.row()
        row.prop(self, "debug", text="Debug Mode")

        row = layout.row()
        row.prop(self, "log_output", text="Log Output")

        row = layout.row()
        row.prop(self, "experimental_features", text="Experimental Features")

        row = layout.row()
        row.prop(self, "check_update_startup", text="Check update on startup")

        layout.prop(self, "clear_sharp_axis_float_prop", text="Clear Sharp Edges Threshold")

        # --- Object Sets ---
        object_sets_settings_box = layout.box()
        row = object_sets_settings_box.row()
        row.label(text="Object Sets Settings")
        row = object_sets_settings_box.row()
        row.prop(addon_object_sets_props, "object_sets_modal_width")
        row = object_sets_settings_box.row()
        row.prop(addon_object_sets_props, "object_sets_list_rows")
        # Object Sets Use Colour
        row = object_sets_settings_box.row()
        row.prop(addon_object_sets_props, "object_sets_use_colour")

        row = object_sets_settings_box.row()
        row.prop(addon_object_sets_props, "object_sets_colour_allow_override")

        if addon_object_sets_props.object_sets_use_colour:
            row = object_sets_settings_box.row()
            row.prop(self, "object_sets_default_colour", text="Default Colour")

        # --- Custom Properties ---
        custom_properties_settings_box = layout.box()
        row = custom_properties_settings_box.row()
        row.label(text="Custom Properties Settings")
        row = custom_properties_settings_box.row()
        row.prop(self, "custom_properties_list_rows")

        # --- Object Attributes ---
        from .data_ops.data_operators import (
            SimpleToolbox_OT_ObjectAttributesRestoreDefaults,
        )

        object_attributes_box = layout.box()
        row = object_attributes_box.row()
        row.label(text="Object Attributes")
        row = object_attributes_box.row(align=True)
        row.prop(self, "object_attributes_to_keep")
        row.operator(SimpleToolbox_OT_ObjectAttributesRestoreDefaults.bl_idname, text="", icon="LOOP_BACK")

        # --- Keymaps ---
        draw_keymap_settings(layout, self)

    def save_axis_threshold(self):
        addon_prefs = bpy.context.preferences.addons[INTERNAL_NAME].preferences
        addon_prefs.clear_sharp_axis_float_prop = self.clear_sharp_axis_float_prop
        # log.info(f"Saved Property: clear_sharp_axis_float_prop -> {self.clear_sharp_axis_float_prop}")


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    AddonPreferences,
]


def register():
    for cls in classes:
        log.debug(f"[INFO] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        log.debug(f"[INFO] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
