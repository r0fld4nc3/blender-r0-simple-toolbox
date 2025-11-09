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


class r0SimpleToolboxEdgeDataProps(bpy.types.PropertyGroup):
    vcol_bevel_layer_name: StringProperty(default="BevelToVcol")  # type: ignore
    vcol_crease_layer_name: StringProperty(default="CreaseToVcol")  # type: ignore

    edge_bweights_presets: PointerProperty(type=R0PROP_PG_EdgeBWeightsPresets)  # type: ignore

    apply_as_bevel_weights: BoolProperty(name="As Bevel Weights", description="Apply selected preset value as Edge Bevel Weight", default=True)  # type: ignore
    apply_as_creases: BoolProperty(name="As Creases", description="Apply selected preset value as Crease", default=False)  # type: ignore

    convert_data_as: EnumProperty(
        name="Apply Data As:",
        description="Choose how to convert the selected preset value",
        items=[
            ("BEVEL_WEIGHTS", "Bevel Weights", "Convert Bevel Weights to Vertex Colours"),
            ("CREASES", "Creases", "Convert Creases to Vertex Colours"),
        ],
        default="BEVEL_WEIGHTS",
    )  # type: ignore

    convert_using_max_value: BoolProperty(
        name="Use Max Value",
        description="Use the highest value among connected edges instead of averaging",
        default=False,
    )  # type: ignore

    apply_value_to_channel_enum: EnumProperty(
        name="Apply to Channel",
        description="Which channel to apply the converted data",
        items=[
            ("R", "R", "Red Channel"),
            ("G", "G", "Green Channel"),
            ("B", "B", "Blue Channel"),
        ],
        # options={"ENUM_FLAG"},  # Allow multiple selections. Default and options become a `set`
        default="R",  # {"R"}
    )  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_BWeightPresetItem,
    R0PROP_PG_EdgeBWeightsPresets,
    r0SimpleToolboxEdgeDataProps,
]


load_post_handlers = [u.initialize_bweight_presets]


def register():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if u.is_debug():
        print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_edge_data_props")
    bpy.types.Scene.r0fl_toolbox_edge_data_props = PointerProperty(
        type=r0SimpleToolboxEdgeDataProps, name="r0fl Toolbox Edge Data"
    )

    for handler in load_post_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    if u.is_debug():
        print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_edge_data_props")
    del bpy.types.Scene.r0fl_toolbox_edge_data_props
