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

from .. import utils as u
from ..export_ops.export_ops import *

log = logging.getLogger(__name__)


class r0SimpleToolbox_PG_FBXExportSettings(bpy.types.PropertyGroup):
    """FBX Export Settings that can be applied globally or per export entry"""

    # Include section
    use_selection: BoolProperty(
        name="Selected Objects", description="Export selected and visible objects only", default=True
    )  # type: ignore

    use_visible: BoolProperty(
        name="Visible Objects", description="Export visible objects only", default=True
    )  # type: ignore

    use_active_collection: BoolProperty(
        name="Active Collection",
        description="Export only objects from the active collection (and its children)",
        default=False,
    )  # type: ignore

    collection: StringProperty(
        name="Source Collection", description="Export only objects from this collection (and its children)", default=""
    )  # type: ignore

    # Object Types - all types from API
    export_empty: BoolProperty(name="Empty", description="Export empty objects", default=False)  # type: ignore

    export_camera: BoolProperty(name="Camera", description="Export camera objects", default=False)  # type: ignore

    export_light: BoolProperty(name="Light", description="Export light objects", default=False)  # type: ignore

    export_armature: BoolProperty(
        name="Armature", description="Export armatures (WARNING: not supported in dupli/group instances)", default=True
    )  # type: ignore

    export_mesh: BoolProperty(name="Mesh", description="Export mesh objects", default=True)  # type: ignore

    export_other: BoolProperty(
        name="Other",
        description="Export other geometry types, like curve, metaball, etc. (converted to meshes)",
        default=True,
    )  # type: ignore

    # Transform
    global_scale: FloatProperty(
        name="Scale",
        description="Scale all data (Some importers do not support scaled armatures!)",
        default=1.0,
        min=0.001,
        max=1000.0,
        soft_min=0.01,
        soft_max=100.0,
    )  # type: ignore

    apply_scale_options: EnumProperty(
        name="Apply Scalings",
        description="How to apply custom and unit scale into FBX scale properties",
        items=[
            (
                "FBX_SCALE_NONE",
                "All Local",
                "Apply custom scaling and units scaling to each object transformation, FBX scale remains at 1.0",
            ),
            (
                "FBX_SCALE_UNITS",
                "FBX Units Scale",
                "Apply custom scaling to each object transformation, and units scaling to FBX scale",
            ),
            (
                "FBX_SCALE_CUSTOM",
                "FBX Custom Scale",
                "Apply custom scaling to FBX scale, and units scaling to each object transformation",
            ),
            ("FBX_SCALE_ALL", "FBX All", "Apply custom scaling and units scaling to FBX scale"),
        ],
        default="FBX_SCALE_NONE",
    )  # type: ignore

    apply_unit_scale: BoolProperty(
        name="Apply Unit", description="Take into account current Blender units settings", default=True
    )  # type: ignore

    use_space_transform: BoolProperty(name="Use Space Transform", description="", default=True)  # type: ignore

    bake_space_transform: BoolProperty(
        name="!EXPERIMENTAL! Apply Transform",
        description="Bake space transform into object data (WARNING: experimental option, use at own risk, known issues with armatures/animations)",
        default=False,
    )  # type: ignore

    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers", description="Apply modifiers to mesh objects", default=True
    )  # type: ignore

    use_mesh_modifiers_render: BoolProperty(
        name="Use Modifiers Render Setting", description="Use render settings when applying modifiers", default=False
    )  # type: ignore

    mesh_smooth_type: EnumProperty(
        name="Smoothing",
        description="Export smoothing information",
        items=[
            ("OFF", "Normals Only", "Export only normals"),
            ("FACE", "Face", "Export face smoothing"),
            ("EDGE", "Edge", "Export edge smoothing"),
        ],
        default="EDGE",
    )  # type: ignore

    colors_type: EnumProperty(
        name="Vertex Colors",
        description="Export vertex color attributes",
        items=[
            ("NONE", "None", "Do not export color attributes"),
            ("LINEAR", "Linear", "Export colors in linear color space"),
            ("SRGB", "sRGB", "Export colors in sRGB color space"),
        ],
        default="SRGB",  # TODO: Consider exporting as sRGB? Seems like it maps better? Test.
    )  # type: ignore

    prioritize_active_color: BoolProperty(
        name="Prioritize Active Color", description="Make sure active color will be exported first", default=True
    )  # type: ignore

    use_subsurf: BoolProperty(
        name="Export Subdivision Surface",
        description="Export subdivision surface (uses last Catmull-Clark subdivision modifier)",
        default=False,
    )  # type: ignore

    use_mesh_edges: BoolProperty(name="Loose Edges", description="Export loose edges", default=False)  # type: ignore

    use_tspace: BoolProperty(
        name="Tangent Space", description="Add binormal and tangent vectors", default=False
    )  # type: ignore

    use_triangles: BoolProperty(
        name="Triangulate Faces", description="Convert all faces to triangles", default=False
    )  # type: ignore

    use_custom_props: BoolProperty(
        name="Custom Properties", description="Export custom properties", default=False
    )  # type: ignore

    # Armature settings
    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones", description="Add dummy leaf bones", default=False
    )  # type: ignore

    primary_bone_axis: EnumProperty(
        name="Primary Bone Axis",
        description="Primary bone axis",
        items=[
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ],
        default="Y",
    )  # type: ignore

    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        description="Secondary bone axis",
        items=[
            ("X", "X Axis", ""),
            ("Y", "Y Axis", ""),
            ("Z", "Z Axis", ""),
            ("-X", "-X Axis", ""),
            ("-Y", "-Y Axis", ""),
            ("-Z", "-Z Axis", ""),
        ],
        default="X",
    )  # type: ignore

    use_armature_deform_only: BoolProperty(
        name="Only Deform Bones", description="Only export deform bones", default=False
    )  # type: ignore

    armature_nodetype: EnumProperty(
        name="Armature FBXNode Type",
        description="FBX node type for armatures",
        items=[
            ("NULL", "Null", ""),
            ("ROOT", "Root", ""),
            ("LIMBNODE", "LimbNode", ""),
        ],
        default="NULL",
    )  # type: ignore

    # Animation settings
    export_animation: BoolProperty(
        name="Animation", description="Export keyframe animation", default=False
    )  # type: ignore

    bake_anim: BoolProperty(name="Baked Animation", description="Export baked animation", default=False)  # type: ignore

    bake_anim_use_all_bones: BoolProperty(
        name="Key All Bones", description="Force export of all bones", default=True
    )  # type: ignore

    bake_anim_use_nla_strips: BoolProperty(
        name="NLA Strips", description="Export NLA strips", default=True
    )  # type: ignore

    bake_anim_use_all_actions: BoolProperty(
        name="All Actions", description="Export all actions", default=True
    )  # type: ignore

    bake_anim_force_startend_keying: BoolProperty(
        name="Force Start/End Keying", description="Always add a keyframe at start and end", default=True
    )  # type: ignore

    bake_anim_step: FloatProperty(
        name="Sampling Rate", description="Sampling rate for animated values", default=1.0, min=0.01, max=100.0
    )  # type: ignore

    bake_anim_simplify_factor: FloatProperty(
        name="Simplify", description="Simplification factor for animation curves", default=1.0, min=0.0, max=100.0
    )  # type: ignore

    # Path and embed
    path_mode: EnumProperty(
        name="Path Mode",
        description="Method used to reference external data",
        items=[
            ("AUTO", "Auto", "Use relative paths where possible"),
            ("ABSOLUTE", "Absolute", "Always use absolute paths"),
            ("RELATIVE", "Relative", "Always use relative paths"),
            ("MATCH", "Match", "Match absolute/relative setting with input path"),
            ("STRIP", "Strip", "Strip path, use only filename"),
            ("COPY", "Copy", "Copy files to export directory"),
        ],
        default="AUTO",
    )  # type: ignore

    embed_textures: BoolProperty(
        name="Embed Textures", description="Embed textures in the FBX file", default=False
    )  # type: ignore

    batch_mode: EnumProperty(
        name="Batch Mode",
        description="Export multiple objects as separate files",
        items=[
            ("OFF", "Off", "Export all objects to one file"),
            ("SCENE", "Scene", "Export each scene to a separate file"),
            ("COLLECTION", "Collection", "Export each collection to a separate file"),
            ("SCENE_COLLECTION", "Scene Collections", "Export each scene collection to a separate file"),
            (
                "ACTIVE_SCENE_COLLECTION",
                "Active Scene Collections",
                "Export active scene collections to separate files",
            ),
        ],
        default="OFF",
    )  # type: ignore

    use_batch_own_dir: BoolProperty(
        name="Batch Own Dir", description="Create a directory for each exported file", default=True
    )  # type: ignore

    use_metadata: BoolProperty(name="Use Metadata", description="Export metadata", default=True)  # type: ignore

    axis_forward: EnumProperty(
        name="Forward",
        description="Forward axis",
        items=[
            ("X", "X Forward", ""),
            ("Y", "Y Forward", ""),
            ("Z", "Z Forward", ""),
            ("-X", "-X Forward", ""),
            ("-Y", "-Y Forward", ""),
            ("-Z", "-Z Forward", ""),
        ],
        default="-Z",
    )  # type: ignore

    axis_up: EnumProperty(
        name="Up",
        description="Up axis",
        items=[
            ("X", "X Up", ""),
            ("Y", "Y Up", ""),
            ("Z", "Z Up", ""),
            ("-X", "-X Up", ""),
            ("-Y", "-Y Up", ""),
            ("-Z", "-Z Up", ""),
        ],
        default="Y",
    )  # type: ignore

    def get_object_types_set(self):
        """Return a set of object types based on boolean properties"""
        types = set()
        if self.export_empty:
            types.add("EMPTY")
        if self.export_camera:
            types.add("CAMERA")
        if self.export_light:
            types.add("LIGHT")
        if self.export_armature:
            types.add("ARMATURE")
        if self.export_mesh:
            types.add("MESH")
        if self.export_other:
            types.add("OTHER")
        return types


class r0SimpleToolbox_PG_ObjectSetName(bpy.types.PropertyGroup):
    """Single object set name entry. Name of Object Set to use for export"""

    name: StringProperty(name="Object Set Name", description="Name of the object set", default="")  # type: ignore

    is_selected: BoolProperty(
        name="Selected", description="Include this object set in the export", default=False
    )  # type: ignore


class r0SimpleToolbox_PG_ExportEntryItem(bpy.types.PropertyGroup):
    """Property representing an entry in the Export List"""

    name: StringProperty(name="Name", default="", description="Export Entry Name")  # type: ignore

    consider_batch_export: BoolProperty(name="Batch", description="Consider this Set for batch exporting", default=False)  # type: ignore

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

    export_at_frame: BoolProperty(
        name="Export at Frame",
        description="Toggle to set which timeline frame to export the objects from",
        default=False,
    )  # type: ignore

    export_frame: IntProperty(
        name="Frame", description="Timeline frame where the objects will be export from", default=1
    )  # type: ignore

    is_global_settings_fbx_expanded: BoolProperty(name="FBX", description="Unfold/Collapse section for Global FBX Export Settings", default=False)  # type: ignore

    use_custom_fbx_settings: BoolProperty(name="Override Global Settings", description="Override global FBX export settings", default=False)  # type: ignore

    export_settings_fbx: PointerProperty(type=r0SimpleToolbox_PG_FBXExportSettings, name="FBX Export Settings", description="FBX Settings for this entry")  # type: ignore

    def get_selected_object_sets(self):
        """Return a list of selected object set names"""
        return [obj_set.name for obj_set in self.object_sets_names if obj_set.is_selected]


class R0PROP_UL_ExportSetsList(bpy.types.UIList):
    """UI List where each entry is an Export Set Item"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from ..export_ops import SimpleToolbox_OT_ExportObjects

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            col = layout.column(align=True)

            header_row = col.row(align=True)
            export_sub_row = header_row.row(align=True)
            export_sub_row.scale_x = 1.1

            # Export Button
            export_op = export_sub_row.operator(SimpleToolbox_OT_ExportObjects.bl_idname, text="", icon="EXPORT")
            # export_op.export_path = item.export_path
            export_op.export_entry_index = index
            export_op.mkdirs_if_not_exist = data.mkdirs_if_not_exist

            if item.use_object_sets:
                selected_object_sets = item.get_selected_object_sets()
                export_op.object_set_names = ", ".join(selected_object_sets)
            else:
                export_op.object_set_names = ""

            # Small separator
            header_row.separator()

            # Export Set Title
            if item.name:
                header_row.prop(item, "name", text="", emboss=False)
            else:
                # Show placeholder text when name is empty
                header_row.prop(
                    item,
                    "name",
                    text="",
                    emboss=False,
                    placeholder=f"Export Set {index + 1}",
                )

            # Uses custom export settings
            if item.use_custom_fbx_settings:
                header_row.label(text="", icon="PREFERENCES")

            # Uses Object Sets
            if item.use_object_sets:
                header_row.label(text="", icon="MESH_CUBE")

            # Export at frame
            if item.export_at_frame:
                header_row.label(text="", icon="KEYTYPE_KEYFRAME_VEC")

            # Small separator
            header_row.separator(factor=1)

            # Consider for batch export
            header_row.prop(item, "consider_batch_export", text="")

            # Button state based on context selection
            if item.use_object_sets:
                selected_sets = item.get_selected_object_sets()
                export_sub_row.enabled = bool(selected_sets) and bool(item.export_path)
            else:
                export_sub_row.enabled = len(u.get_selected_objects()) > 0 and bool(item.export_path)

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text=item.name or f"Export {index + 1}")


class r0SimpleToolbox_PG_ExportProps(bpy.types.PropertyGroup):
    export_sets_list_rows: IntProperty(name="Export Sets List Rows", default=6, min=1)  # type: ignore

    mkdirs_if_not_exist: BoolProperty(name="Create sub-paths", description="If chosen path does not exist in the filesystem, create the full path including sub-directories", default=True)  # type: ignore

    export_sets: CollectionProperty(
        type=r0SimpleToolbox_PG_ExportEntryItem, name="Export Sets", description=""
    )  # type: ignore

    active_index: IntProperty(
        name="Export Sets Index", description="Index of the active export set", default=0
    )  # type: ignore

    show_edit_global_fbx_export_settings: BoolProperty(name="Edit Global Settings (FBX)", description="Edit export options applied globally across Export Sets", default=False)  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
# fmt: off
classes = [
    r0SimpleToolbox_PG_FBXExportSettings,
    r0SimpleToolbox_PG_ObjectSetName,
    r0SimpleToolbox_PG_ExportEntryItem,
    R0PROP_UL_ExportSetsList,
    r0SimpleToolbox_PG_ExportProps,
]
# fmt: on


load_post_handlers = []


def register():
    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if u.is_debug():
        log.debug(f"Register bpy.types.Scene.r0fl_toolbox_export_props")
    bpy.types.Scene.r0fl_toolbox_export_props = PointerProperty(
        type=r0SimpleToolbox_PG_ExportProps, name="r0fl Toolbox Export"
    )


def unregister():
    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
    log.debug(f"Unregister bpy.types.Scene.r0fl_toolbox_export_props")
    del bpy.types.Scene.r0fl_toolbox_export_props
