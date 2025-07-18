from pathlib import Path

import bpy
from bpy.props import BoolProperty, FloatVectorProperty, IntProperty, StringProperty

from .. import utils as u
from .export_ops import *

_mod = "EXPORT.OPERATORS"


class SimpleToolbox_OT_SelectPath(bpy.types.Operator):
    bl_idname = "r0tools.select_quick_export_path"
    bl_label = "Select"
    bl_description = "Open file browser to select a directory path"

    filepath: StringProperty(name="Path", description="Path to a directory", subtype="FILE_PATH", default="Untitled.fbx")  # type: ignore

    filename_ext = ".fbx"

    file_extension: StringProperty(
        name="Extension", description="File extension to use", default=".fbx", options={"HIDDEN"}
    )  # type: ignore

    filter_glob: StringProperty(default=f"*.fbx", options={"HIDDEN"})  # type: ignore

    directory: StringProperty(
        name="Directory", description="Directory path without filename", options={"SKIP_SAVE"}
    )  # type: ignore

    # Where to apply the data
    index: IntProperty(
        name="Export Set Index", description="Index of the export set to update", default=0, options={"HIDDEN"}
    )  # type: ignore

    def check(self, context):
        """Called when filename changes in the file browser"""
        change = False
        filepath = Path(self.filepath)

        if not filepath.suffix or filepath.suffix.lower() != self.file_extension.lower():
            self.filepath = str(filepath.with_suffix(self.file_extension))
            change = True

        return change

    def invoke(self, context, event):
        self.filter_glob = f"*{self.file_extension}"
        self.filename_ext = self.file_extension

        addon_export_props = u.get_addon_export_props()

        # Get the current export set path if it exists
        if 0 <= self.index < len(addon_export_props.export_sets):
            current_path = addon_export_props.export_sets[self.index].export_path
            if current_path:
                self.filepath = current_path

        # Open the file browser, configured to use the 'filepath' property to store the result
        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}

    def execute(self, context):
        addon_export_props = u.get_addon_export_props()

        # Index valid?
        if not (0 <= self.index < len(addon_export_props.export_sets)):
            self.report({"ERROR"}, "Invalid export set index")
            return {"CANCELLED"}

        filepath = Path(self.filepath)

        # Ensure correct extension
        if not filepath.suffix:
            filepath = filepath.with_suffix(self.file_extension)
        elif filepath.suffix != self.file_extension:
            filepath = filepath.with_suffix(self.file_extension)

        # Validate directory exists or find closest existing parent
        directory_path = filepath.parent
        if not directory_path.exists():
            while not directory_path.exists() and directory_path != directory_path.parent:
                directory_path = directory_path.parent

            if directory_path.exists():
                self.directory = str(directory_path)
                self.report({"WARNING"}, f"Adjusted directory to: {directory_path}")

        addon_export_props.export_sets[self.index].export_path = str(filepath)

        self.report(
            {"INFO"}, f"Set export path for '{addon_export_props.export_sets[self.index].export_set_name}': {filepath}"
        )

        return {"FINISHED"}


class SimpleToolbox_OT_AddExportSet(bpy.types.Operator):
    bl_label = "Add"
    bl_idname = "r0tools.export_sets_add"
    bl_description = "Add a new Export Set entry"
    bl_options = {"REGISTER"}

    def execute(self, context):
        addon_export_props = u.get_addon_export_props()

        new_set = get_export_sets().add()

        return {"FINISHED"}


class SimpleToolbox_OT_RemoveExportSet(bpy.types.Operator):
    bl_label = "Remove"
    bl_idname = "r0tools.export_sets_remove"
    bl_description = "Remove selected Export Set entry"
    bl_options = {"REGISTER"}

    index: IntProperty(name="Index", description="Index of export set to remove", default=-1)  # type: ignore

    def execute(self, context):
        addon_export_props = u.get_addon_export_props()
        use_list_view = addon_export_props.use_list_view

        index = get_active_export_set_index() if use_list_view else self.index

        if 0 <= index < get_export_sets_count():
            remove_export_set_at_index(index)
            set_active_export_set_index(max(0, index - 1))
            self.report({"INFO"}, f"Removed Export Set: {index}")

        return {"FINISHED"}


class SimpleToolbox_OT_RenameExportSet(bpy.types.Operator):
    bl_label = "Rename"
    bl_idname = "r0tools.rename_export_set"
    bl_description = "Rename the selected Export Set entry"

    new_name: StringProperty(name="New Object Set Name", default="")  # type: ignore

    def invoke(self, context, event):
        index = get_active_export_set_index()

        if 0 <= index < get_export_sets_count():
            export_set = get_export_set_at_index(index)
            self.new_name = export_set.name

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        index = get_active_export_set_index()

        if 0 <= index < get_export_sets_count():
            export_set = get_export_set_at_index(index)
            old_name = export_set.name
            success = set_export_set_name(export_set, self.new_name)
            if success:
                self.report({"INFO"}, f"Renamed '{old_name}' to '{self.new_name}'")

        return {"FINISHED"}


class SimpleToolbox_OT_ToggleObjectSetSelection(bpy.types.Operator):
    """Toggle object set selection for export"""

    bl_idname = "r0tools.toggle_object_set_selection"
    bl_label = "Toggle Object Set"
    bl_options = {"REGISTER", "UNDO"}

    export_set_index: IntProperty()  # type: ignore
    object_set_name: StringProperty()  # type: ignore

    def execute(self, context):
        export_props = u.get_addon_export_props()

        if 0 <= self.export_set_index < len(export_props.export_sets):
            export_item = export_props.export_sets[self.export_set_index]

            # Find if this object set is already in the collection
            found = None
            for obj_set in export_item.object_sets_names:
                if obj_set.name == self.object_set_name:
                    found = obj_set
                    break

            if found:
                found.is_selected = not found.is_selected
            else:
                new_entry = export_item.object_sets_names.add()
                new_entry.name = self.object_set_name
                new_entry.is_selected = True

        return {"FINISHED"}


class SimpleToolbox_OT_ExportObjects(bpy.types.Operator):
    bl_label = "Quick Export"
    bl_idname = "r0tools.quick_export_objects"
    bl_description = "Export Selection"
    bl_options = {"REGISTER"}

    export_path: StringProperty(name="")  # type: ignore
    mkdirs_if_not_exist: BoolProperty(name="Create sub-paths", description="If chosen path does not exist in the filesystem, create the full path including sub-directories", default=False)  # type: ignore

    object_set_names: StringProperty(
        name="Object Set Names", description="Comma-separated list of object set names to export", default=""
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT

    def execute(self, context):
        # Store current selection to restore later
        original_selection = u.get_selected_objects()
        original_active = u.get_active_object()

        try:
            # Clear current selection
            u.deselect_all()

            # If we have object set names, select objects from those sets
            if self.object_set_names:
                object_set_names_list = [name.strip() for name in self.object_set_names.split(",") if name.strip()]

                # Get all object sets
                object_sets = u.get_object_sets()

                # Select objects from specified object sets
                objects_to_export = set()
                for obj_set in object_sets:
                    if obj_set.name in object_set_names_list:
                        # Get objects from this object set
                        for obj_ref in obj_set.objects:
                            obj = bpy.data.objects[obj_ref.object.name]
                            objects_to_export.add(obj)

                # Select all objects to export
                for obj in objects_to_export:
                    u.select_object(obj, add=True, set_active=True)

                if not objects_to_export:
                    self.report({"WARNING"}, "No objects found in specified object sets")
                    return {"CANCELLED"}
            else:
                # Use current selection if no object sets specified
                if not original_selection:
                    self.report({"WARNING"}, "No objects selected and no object sets specified")
                    return {"CANCELLED"}

                # Restore original selection for export
                for obj in original_selection:
                    u.select_object(obj, add=True, set_active=True)

            # Export path handling
            export_path = self.export_path
            if not export_path:
                self.report({"WARNING"}, "No export path defined")
                return {"CANCELLED"}

            export_path = Path(export_path)

            # Ensure .fbx extension
            if not export_path.suffix:
                export_path = export_path.with_suffix(".fbx")
            elif export_path.suffix.lower() != ".fbx":
                export_path = export_path.with_suffix(".fbx")

            # Create path if it doesn't exist
            directory = export_path.parent
            if not directory.exists():
                if self.mkdirs_if_not_exist:
                    directory.mkdir(parents=True, exist_ok=True)
                    self.report({"INFO"}, f"Created directories: {directory}")
                else:
                    self.report({"ERROR"}, f"Export directory does not exist: {directory}")
                    return {"CANCELLED"}

            bpy.ops.export_scene.fbx(
                filepath=str(export_path),
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

            self.report({"INFO"}, f"Exported to: {export_path}")

        finally:
            # Restore original selection
            u.deselect_all()

            for obj in original_selection:
                u.select_object(obj, add=True)

            u.set_active_object(original_active)

        return {"FINISHED"}


# ===================================================================
#   Register & Unregister
# ===================================================================

# fmt: off
classes = [
    SimpleToolbox_OT_SelectPath,
    SimpleToolbox_OT_AddExportSet,
    SimpleToolbox_OT_RemoveExportSet,
    SimpleToolbox_OT_RenameExportSet,
    SimpleToolbox_OT_ToggleObjectSetSelection,
    SimpleToolbox_OT_ExportObjects,
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
