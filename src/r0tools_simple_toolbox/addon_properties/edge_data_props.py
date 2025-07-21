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
from ..defines import DEBUG

_mod = "EDGE DATA PROPS"


###################################
###### Edge Data Ops & Items ######
###################################
class R0PROP_BWeightPresetItem(bpy.types.PropertyGroup):
    """Individual bevel weight preset item"""

    value: FloatProperty(
        name="Bevel Weight", description="Bevel weight value", default=0.0, min=0.0, max=1.0
    )  # type: ignore


class R0PROP_PG_EdgeBWeightsPresets(bpy.types.PropertyGroup):
    """Collection of bevel weight presets"""

    presets: CollectionProperty(type=R0PROP_BWeightPresetItem)  # type: ignore
    active_index: IntProperty(default=0, description="Active Index")  # type: ignore


class R0PROP_UL_EdgeBWeightsList(bpy.types.UIList):
    """UI List for bevel weight presets"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from ..data_ops import SimpleToolbox_OT_ApplyBWeightPreset

        # Info Row
        item_row = layout.row(align=True)

        # Apply Preset Button
        col_apply = item_row.row(align=True)
        """
        Store a reference to the Operator and assign it the preset_index property
        so we can apply the specific preset value at this row/index
        without having to first select the row!
        """
        op = col_apply.operator(SimpleToolbox_OT_ApplyBWeightPreset.bl_idname, text="", icon="PLUS")
        # Set the property before adding to layout
        op.preset_index = index
        op.value = item.value
        # Add spacing after the operation is complete
        col_apply.separator(factor=0.5)

        # Preset Value
        item_value = f"{item.value*100:.2f}".split(".")[0] + "%"
        col_value = item_row.row(align=True)
        col_value.label(text=item_value, icon="NONE")

        # Fill space
        item_row.separator(factor=1.0)


class r0SimpleToolboxEdgeDataProps(bpy.types.PropertyGroup):
    vcol_bevel_layer_name: StringProperty(default="BevelToVcol")  # type: ignore
    vcol_crease_layer_name: StringProperty(default="CreaseToVcol")  # type: ignore

    edge_bweights_presets: PointerProperty(type=R0PROP_PG_EdgeBWeightsPresets)  # type: ignore

    apply_as_bevel_weights: BoolProperty(name="As Bevel Weights", description="Apply selected preset value as Edge Bevel Weight", default=True)  # type: ignore
    apply_as_creases: BoolProperty(name="As Creases", description="Apply selected preset value as Crease", default=False)  # type: ignore

    bevel_weights_to_vcol: BoolProperty(name="Bevel Weights", description="Convert Bevel Edge Weights to Vertex Colours", default=True)  # type: ignore

    crease_to_vcol: BoolProperty(name="Creases", description="Convert Creases to Vertex Colours", default=False)  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_BWeightPresetItem,
    R0PROP_PG_EdgeBWeightsPresets,
    R0PROP_UL_EdgeBWeightsList,
    r0SimpleToolboxEdgeDataProps,
]


load_post_handlers = [u.initialize_bweight_presets]


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if DEBUG:
        print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_edge_data_props")
    bpy.types.Scene.r0fl_toolbox_edge_data_props = PointerProperty(type=r0SimpleToolboxEdgeDataProps)

    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    if DEBUG:
        print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_edge_data_props")
    del bpy.types.Scene.r0fl_toolbox_edge_data_props
