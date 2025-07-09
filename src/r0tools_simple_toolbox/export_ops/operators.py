from pathlib import Path

import bpy
from bpy.props import BoolProperty, FloatVectorProperty, IntProperty, StringProperty

from .. import utils as u

_mod = "EXPORT.OPERATORS"


class SimpleToolbox_OT_SelectPath(bpy.types.Operator):
    bl_idname = "r0tools.select_path"
    bl_label = "Select Directory Path"
    bl_description = "Open file browser to select a directory path"

    filepath: StringProperty(name="Path", description="Path to a directory", subtype="DIR_PATH")  # type: ignore

    def invoke(self, context, event):
        # Open the file browser, configured to use the 'filepath' property to store the result
        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}

    def execute(self, context):
        export_props = u.get_addon_export_props()

        filepath = Path(self.filepath)

        if filepath.exists():
            if filepath.is_file():
                filepath = filepath.parent
        else:
            # Let's do .parent until filepath exists or reaches top
            while True:
                filepath = filepath.parent

                if filepath.exists():
                    break

            self.report({"WARNING"}, "Path differs from original")

        filepath_str = str(filepath)

        export_props.export_path = filepath_str

        return {"FINISHED"}


class SimpleToolbox_OT_ExportSelectedObjects(bpy.types.Operator):
    bl_label = "Export Selection"
    bl_idname = "r0tools.remove_object_set"
    bl_description = "Remove the selected Object Set entry"
    bl_options = {"REGISTER", "UNDO"}

    export_path: StringProperty(name="")  # type: ignore
    export_name: StringProperty(name="")  # type: ignore
    mkdirs_if_not_exist: BoolProperty(name="Create sub-paths", description="If chosen path does not exist in the filesystem, create the full path including sub-directories", default=False)  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT and len(u.get_object_sets()) > 0

    def execute(self, context):
        export_props = u.get_addon_export_props()

        export_path = export_props.export_path if not self.export_path else self.export_path
        export_name = export_props.export_file_name if not self.export_name else self.export_name
        mkdirs = export_props.mkdirs_if_not_exist if not self.mkdirs_if_not_exist else self.mkdirs_if_not_exist

        if not export_path:
            self.report({"WARNING"}, "No export path defined")
            return {"CANCELLED"}

        if not export_name:
            self.report({"WARNING"}, "No export file name defined")
            return {"CANCELLED"}

        export_path = Path(export_path)

        if mkdirs:
            export_path.mkdir(parents=True, exist_ok=True)

        if not export_path.exists():
            self.report({"WARNING"}, "Export path does not exist")
            return {"CANCELLED"}

        if not export_path.is_dir():
            self.report({"WARNING"}, "Export path is not a directory")
            return {"CANCELLED"}

        if str(export_name).lower().endswith("."):
            export_name = f"{export_name}fbx"

        if not str(export_name).lower().endswith(".fbx"):
            export_name = f"{export_name}.fbx"

        export_path_file = export_path / export_name

        bpy.ops.export_scene.fbx(
            filepath=str(export_path_file),
            check_existing=False,
            filter_glob="*.fbx",
            use_selection=True,
            use_visible=False,
            use_active_collection=False,
            collection="",
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_NONE",
            use_space_transform=True,
            bake_space_transform=False,
            object_types={"ARMATURE", "MESH", "OTHER"},
            use_mesh_modifiers=True,
            use_mesh_modifiers_render=False,
            mesh_smooth_type="EDGE",
            colors_type="LINEAR",
            prioritize_active_color=True,
            use_subsurf=False,
            use_mesh_edges=False,
            use_tspace=False,
            use_triangles=False,
            use_custom_props=False,
            add_leaf_bones=False,
            primary_bone_axis="Y",
            secondary_bone_axis="X",
            use_armature_deform_only=False,
            armature_nodetype="NULL",
            bake_anim=False,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=1.0,
            path_mode="AUTO",
            embed_textures=False,
            batch_mode="OFF",
            use_batch_own_dir=True,
            use_metadata=True,
            axis_forward="-Z",
            axis_up="Y",
        )

        return {"FINISHED"}


# ===================================================================
#   Register & Unregister
# ===================================================================

# fmt: off
classes = [
    SimpleToolbox_OT_SelectPath,
    SimpleToolbox_OT_ExportSelectedObjects,
]
# fmt: on


def register():
    for cls in classes:
        print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
