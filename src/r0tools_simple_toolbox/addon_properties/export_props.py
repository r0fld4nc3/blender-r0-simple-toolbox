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
        name="Toggle Object Sets List",
        description="Toggles a list to check which Object Sets to use for export",
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

        left_padding_factor = 0.03
        path_row_height_scale = 1.2
        entry_separation_factor = 2.0
        export_button_width_scale = 1.5

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # Use column for vertical stacking
            # box = layout.box()
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

            # Second row
            path_row = col.row(align=True)
            path_row.scale_y = path_row_height_scale

            split = path_row.split(factor=left_padding_factor)
            split.label(text="")

            right_row = split.row(align=True)

            # Export button (in a sub-row) so we can have red button
            export_sub_row = right_row.row(align=True)
            export_sub_row.scale_x = export_button_width_scale
            export_sub_row.alert = True

            export_op = export_sub_row.operator(SimpleToolbox_OT_ExportObjects.bl_idname, text="", icon="EXPORT")
            export_op.export_path = item.export_path
            export_op.mkdirs_if_not_exist = data.mkdirs_if_not_exist

            if item.use_object_sets:
                selected_object_sets = item.get_selected_object_sets()
                export_op.object_set_names = ", ".join(selected_object_sets)
            else:
                export_op.object_set_names = ""

            # Path and Select
            right_row.prop(item, "export_path", text="")
            op = right_row.operator(SimpleToolbox_OT_SelectPath.bl_idname, text="", icon="FILE_FOLDER")
            op.index = index

            # Use Object Sets button
            right_row.prop(
                item, "use_object_sets", text="", icon="MESH_CUBE" if item.use_object_sets else "RESTRICT_SELECT_OFF"
            )

            # Object Sets Row
            object_sets_row = layout.row()
            if item.use_object_sets:
                available_sets = u.get_object_sets()

                if available_sets:
                    selected_names = {obj_set.name for obj_set in item.object_sets_names if obj_set.is_selected}

                    object_sets_row = col.row()

                    # Create Left Spacer to following indentation
                    split = object_sets_row.split(factor=left_padding_factor)
                    split.label(text="")  # Empty left margin

                    # Sub-row left align contents
                    right_side = split.row(align=True)
                    right_side.alignment = "LEFT"

                    right_side.prop(
                        item,
                        "object_sets_expanded",
                        text="Choose Object Sets",
                        icon="TRIA_DOWN" if item.object_sets_expanded else "TRIA_RIGHT",
                        emboss=False,
                    )

                    # Empty space to push contents to left
                    right_side.label(text="")

                    if item.object_sets_expanded:
                        # Box for object sets with same indentation
                        box_row = col.row()
                        box_split = box_row.split(factor=left_padding_factor)
                        box_split.label(text="")

                        object_sets_box = box_split.box()
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
                                SimpleToolbox_OT_ToggleObjectSetSelection.bl_idname, text="", icon=icon, emboss=False
                            )
                            op.export_set_index = index
                            op.object_set_name = obj_set.name

                            set_row.separator(factor=1.0)

                            set_row.label(text=obj_set.name)
                else:
                    # Also indent the "No Object Sets" message
                    no_sets_row = col.row()
                    split = no_sets_row.split(factor=left_padding_factor)
                    split.label(text="")
                    split.label(text="No Object Sets available", icon="INFO")

            # Button state based on context selection
            if item.use_object_sets:
                selected_sets = item.get_selected_object_sets()
                export_sub_row.enabled = bool(selected_sets) and bool(item.export_path)
            else:
                export_sub_row.enabled = len(u.get_selected_objects()) > 0 and bool(item.export_path)

            # Add spacing between items
            col.separator(factor=entry_separation_factor)

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

    use_list_view: BoolProperty(name="List View Toggle", description="Toggle between List view and Row view", default=False)  # type: ignore


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
