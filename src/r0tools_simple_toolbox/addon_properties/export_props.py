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

_mod = "EXPORT PROPS"


class r0SimpleToolbox_PG_ObjectSetName(bpy.types.PropertyGroup):
    """Single object set name entry. Name of Object Set to use for export"""

    name: StringProperty(name="Object Set Name", description="Name of the object set", default="")  # type: ignore


class r0SimpleToolbox_PG_ExportEntryItem(bpy.types.PropertyGroup):
    """Property representing an entry in the Export List"""

    export_set_name: StringProperty(name="Name", default="", description="Export Entry Name")  # type: ignore

    use_object_sets: BoolProperty(
        name="Use Object Sets",
        description="Pick Object Sets from the Object Sets list that describe what to export",
        default=False,
    )  # type: ignore

    object_sets_names: CollectionProperty(
        type=r0SimpleToolbox_PG_ObjectSetName, name="Object Set Names", description="List of object set names to export"
    )  # type: ignore

    export_path: StringProperty(
        name="Path", default="", description="Full filepath of file to be exported"
    )  # type: ignore | subtype="FILE_PATH" to add a built-in button to select path


class R0PROP_UL_ExportSetsList(bpy.types.UIList):
    """UI List where each entry is an Export Set Item"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from ..export_ops import (
            SimpleToolbox_OT_ExportSelectedObjects,
            SimpleToolbox_OT_SelectPath,
        )

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # Use column for vertical stacking instead of box()
            col = layout.column(align=True)

            # First row
            header_row = col.row(align=True)
            if item.export_set_name:
                header_row.prop(item, "export_set_name", text="", emboss=False)
            else:
                # Show placeholder text when name is empty
                header_row.prop(
                    item,
                    "export_set_name",
                    text="",
                    emboss=False,
                    placeholder=f"Export Set {index + 1}",
                )

            # header_row.prop(item, "use_object_sets", text="", icon="GROUP" if item.use_object_sets else "OBJECT_DATA")

            # Second row
            path_row = col.row(align=True)
            path_row.scale_y = 1.2
            path_row.prop(item, "export_path", text="")
            op = path_row.operator(SimpleToolbox_OT_SelectPath.bl_idname, text="", icon="FILE_FOLDER")
            op.index = index
            path_row.operator(SimpleToolbox_OT_ExportSelectedObjects.bl_idname, text="", icon="EXPORT")

            # Separator between items
            col.separator(factor=0.5)

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text=item.export_set_name or f"Export {index + 1}")


class r0SimpleToolbox_PG_ExportProps(bpy.types.PropertyGroup):
    mkdirs_if_not_exist: BoolProperty(name="Create sub-paths", description="If chosen path does not exist in the filesystem, create the full path including sub-directories", default=False)  # type: ignore

    export_sets: CollectionProperty(
        type=r0SimpleToolbox_PG_ExportEntryItem, name="Export Sets", description=""
    )  # type: ignore

    active_index: IntProperty(
        name="Export Sets Index", description="Index of the active export set", default=0
    )  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
# fmt: off
classes = [
    r0SimpleToolbox_PG_ObjectSetName,
    r0SimpleToolbox_PG_ExportEntryItem,
    R0PROP_UL_ExportSetsList,
    r0SimpleToolbox_PG_ExportProps
]
# fmt: on


load_post_handlers = []


def register():
    for cls in classes:
        print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_export_props")
    bpy.types.Scene.r0fl_toolbox_export_props = PointerProperty(type=r0SimpleToolbox_PG_ExportProps)


def unregister():
    print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_export_props")
    del bpy.types.Scene.r0fl_toolbox_export_props

    for cls in classes:
        print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
