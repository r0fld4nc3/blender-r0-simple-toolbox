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

    is_selected: BoolProperty(
        name="Selected", description="Include this object set in the export", default=False
    )  # type: ignore


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

    object_sets_expanded: BoolProperty(
        name="Object Sets",
        description="",
        default=False,
    )  # type: ignore

    export_path: StringProperty(
        name="Path", default="", description="Full filepath of file to be exported"
    )  # type: ignore | subtype="FILE_PATH" to add a built-in button to select path

    def get_selected_object_sets(self):
        """Return a list of selected object set names"""
        return [obj_set.name for obj_set in self.object_sets_names if obj_set.is_selected]


class R0PROP_UL_ExportSetsList(bpy.types.UIList):
    """UI List where each entry is an Export Set Item"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from ..export_ops import (
            SimpleToolbox_OT_ExportObjects,
            SimpleToolbox_OT_SelectPath,
            SimpleToolbox_OT_ToggleObjectSetSelection,
        )

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # Use column for vertical stacking
            box = layout.box()
            col = box.column(align=True)

            # First row
            header_row = col.row(align=True)

            # Use Object Sets
            header_row.prop(
                item, "use_object_sets", text="", icon="MESH_CUBE" if item.use_object_sets else "RESTRICT_SELECT_OFF"
            )

            header_row.separator(factor=1)

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

            # Object Sets Row
            if item.use_object_sets:
                available_sets = u.get_object_sets()

                if available_sets:
                    selected_names = {obj_set.name for obj_set in item.object_sets_names if obj_set.is_selected}

                    object_sets_row = col.row()

                    object_sets_row.prop(
                        item,
                        "object_sets_expanded",
                        text="",
                        icon="TRIA_DOWN" if item.object_sets_expanded else "TRIA_RIGHT",
                        emboss=False,
                    )

                    if item.object_sets_expanded:
                        object_sets_box = col.box()
                        object_sets_col = object_sets_box.column(align=True)

                        # Draw each available object set
                        for obj_set in available_sets:
                            if obj_set.separator:
                                continue

                            set_row = object_sets_col.row(align=True)

                            # Check if this set is in our collection and selected
                            is_selected = obj_set.name in selected_names
                            icon = "CHECKBOX_HLT" if is_selected else "CHECKBOX_DEHLT"

                            # Toggle selection with purpose-built Operator
                            op = set_row.operator(
                                SimpleToolbox_OT_ToggleObjectSetSelection.bl_idname, text="", icon=icon
                            )
                            op.export_set_index = index
                            op.object_set_name = obj_set.name

                            set_row.separator(factor=1.0)

                            set_row.label(text=obj_set.name)
                else:
                    col.label(text="No Object Sets available", icon="INFO")

            # Second row
            path_row = col.row(align=True)
            path_row.scale_y = 1.2

            # Export button (in a sub-row)
            export_sub_row = path_row.row(align=True)
            export_sub_row.scale_x = 1.2
            export_sub_row.alert = True

            # Button state based on context selection
            if item.use_object_sets:
                selected_sets = item.get_selected_object_sets()
                export_sub_row.enabled = bool(selected_sets) and bool(item.export_path)
            else:
                export_sub_row.enabled = len(u.get_selected_objects()) > 0 and bool(item.export_path)

            export_op = export_sub_row.operator(SimpleToolbox_OT_ExportObjects.bl_idname, text="", icon="EXPORT")
            export_op.export_path = item.export_path
            export_op.mkdirs_if_not_exist = data.mkdirs_if_not_exist

            if item.use_object_sets:
                selected_object_sets = item.get_selected_object_sets()
                export_op.object_set_names = ", ".join(selected_object_sets)
            else:
                export_op.object_set_names = ""

            # Path and Select
            path_row.prop(item, "export_path", text="")
            op = path_row.operator(SimpleToolbox_OT_SelectPath.bl_idname, text="", icon="FILE_FOLDER")
            op.index = index

            # Add spacing between items
            col.separator(factor=4.0)

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
