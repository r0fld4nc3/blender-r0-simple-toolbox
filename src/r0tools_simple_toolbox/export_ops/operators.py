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
        name="Directory", description="Directory path without filename", subtype="DIR_PATH", options={"SKIP_SAVE"}
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

        self.report({"INFO"}, f"Set export path for '{addon_export_props.export_sets[self.index].name}': {filepath}")

        return {"FINISHED"}


class SimpleToolbox_OT_AddExportSet(bpy.types.Operator):
    bl_label = "Add"
    bl_idname = "r0tools.export_sets_add"
    bl_description = "Add a new Export Set entry"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        addon_export_props = u.get_addon_export_props()

        new_set = get_export_sets().add()

        set_active_export_set_index(get_export_sets_count() - 1)

        return {"FINISHED"}


class SimpleToolbox_OT_RemoveExportSet(bpy.types.Operator):
    bl_label = "Remove"
    bl_idname = "r0tools.export_sets_remove"
    bl_description = "Remove selected Export Set entry"
    bl_options = {"REGISTER", "UNDO"}

    index: IntProperty(name="Index", description="Index of export set to remove", default=-1)  # type: ignore

    @classmethod
    def poll(cls, context):
        accepted_contexts = context.mode in [u.OBJECT_MODES.OBJECT]
        has_sets = get_export_sets()
        return accepted_contexts and has_sets

    def execute(self, context):
        index = get_active_export_set_index()

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

    mkdirs_if_not_exist: BoolProperty(name="Create sub-paths", description="If chosen path does not exist in the filesystem, create the full path including sub-directories", default=False)  # type: ignore

    object_set_names: StringProperty(
        name="Object Set Names", description="Comma-separated list of object set names to export", default=""
    )  # type: ignore

    # Add index to identify which export entry
    export_entry_index: IntProperty(
        name="Export Entry Index", description="Index of the export entry being used", default=-1
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        # NOTE: For the other ways to "poll" check the `export_sub_row.enabled`
        # section in export_props.py in draw_item, where it dynamically
        # update this Operator based on conditions
        accepted_contexts = context.mode in [u.OBJECT_MODES.OBJECT]
        export_sets = get_export_sets()

        return accepted_contexts and export_sets

    def execute(self, context):
        # Get the export settings
        addon_prefs = u.get_addon_prefs()

        settings = addon_prefs.export_settings_global_fbx

        export_item = get_export_set_at_index(self.export_entry_index)
        if export_item:
            # Uses custom FBX settings?
            if export_item.use_custom_fbx_settings:
                settings = export_item.export_settings_fbx

        # Store current selection to restore later
        original_selection = u.get_selected_objects()
        original_active = u.get_active_object()

        # Store current timeline frame
        original_timeline_frame = u.get_scene().frame_current

        states_modified = []

        viewport_was_local = u.is_viewport_local()
        if viewport_was_local:
            u.toggle_viewport_local_mode()

        # No valid selection when not using Object Sets
        if not export_item.use_object_sets and not u.get_selected_objects():
            return {"CANCELLED"}

        try:
            # Clear current selection
            u.deselect_all()

            # Set timeline frame if using it
            if export_item.export_at_frame:
                u.get_scene().frame_current = export_item.export_frame

            # If the export item is using Objet Sets and we have Object Set names, select objects from those sets
            if export_item.use_object_sets and self.object_set_names:
                object_set_names_list = [name.strip() for name in self.object_set_names.split(",") if name.strip()]

                # Get all object sets
                object_sets = u.get_object_sets()

                # Select objects from specified object sets
                objects_to_export = set()
                for obj_set in object_sets:
                    if obj_set.name in object_set_names_list:
                        # Get objects from this object set
                        for obj_ref in obj_set.objects:
                            obj = obj_ref.object
                            if obj and obj.name in bpy.data.objects:
                                objects_to_export.add(obj)

                # Select all objects to export
                for obj in objects_to_export:
                    # Unhide if necessary and track changes
                    modified = u.unhide_object_and_collections(obj)
                    states_modified.extend(modified)

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
            export_path = export_item.export_path
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
                use_selection=settings.use_selection,
                use_visible=settings.use_visible,
                use_active_collection=settings.use_active_collection,
                collection=settings.collection,
                global_scale=settings.global_scale,
                apply_unit_scale=settings.apply_unit_scale,
                apply_scale_options=settings.apply_scale_options,
                use_space_transform=settings.use_space_transform,
                bake_space_transform=settings.bake_space_transform,
                object_types=settings.get_object_types_set(),
                use_mesh_modifiers=settings.use_mesh_modifiers,
                use_mesh_modifiers_render=settings.use_mesh_modifiers_render,
                mesh_smooth_type=settings.mesh_smooth_type,
                colors_type=settings.colors_type,
                prioritize_active_color=settings.prioritize_active_color,
                use_subsurf=settings.use_subsurf,
                use_mesh_edges=settings.use_mesh_edges,
                use_tspace=settings.use_tspace,
                use_triangles=settings.use_triangles,
                use_custom_props=settings.use_custom_props,
                add_leaf_bones=settings.add_leaf_bones,
                primary_bone_axis=settings.primary_bone_axis,
                secondary_bone_axis=settings.secondary_bone_axis,
                use_armature_deform_only=settings.use_armature_deform_only,
                armature_nodetype=settings.armature_nodetype,
                # Use main toggle to handle properties
                bake_anim=settings.export_animation and settings.bake_anim,
                bake_anim_use_all_bones=settings.bake_anim_use_all_bones and settings.bake_anim,
                bake_anim_use_nla_strips=settings.bake_anim_use_nla_strips and settings.bake_anim,
                bake_anim_use_all_actions=settings.bake_anim_use_all_actions and settings.bake_anim,
                bake_anim_force_startend_keying=settings.bake_anim_force_startend_keying and settings.bake_anim,
                bake_anim_step=settings.bake_anim_step,
                bake_anim_simplify_factor=settings.bake_anim_simplify_factor,
                path_mode=settings.path_mode,
                embed_textures=settings.embed_textures,
                batch_mode=settings.batch_mode,
                use_batch_own_dir=settings.use_batch_own_dir,
                use_metadata=settings.use_metadata,
                axis_forward=settings.axis_forward,
                axis_up=settings.axis_up,
            )

            self.report({"INFO"}, f"Exported to: {export_path}")

        finally:
            u.get_scene().frame_current = original_timeline_frame

            # Restore original selection
            u.deselect_all()

            for obj in original_selection:
                u.select_object(obj, add=True)

            u.set_active_object(original_active)

            # Restore original visibility state
            u.restore_visibility_state(states_modified)

            if viewport_was_local:
                u.toggle_viewport_local_mode()

        return {"FINISHED"}


class SimpleToolbox_OT_BatchExportObjects(bpy.types.Operator):
    bl_label = "Batch Export"
    bl_idname = "r0tools.batch_export_object_sets"
    bl_description = "Batch export sets that have been marked as such"
    bl_options = {"REGISTER"}

    mkdirs_if_not_exist: BoolProperty(name="Create sub-paths", description="If chosen path does not exist in the filesystem, create the full path including sub-directories", default=False)  # type: ignore

    object_set_names: StringProperty(
        name="Object Set Names", description="Comma-separated list of object set names to export", default=""
    )  # type: ignore

    # Add index to identify which export entry
    export_entry_index: IntProperty(
        name="Export Entry Index", description="Index of the export entry being used", default=-1
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        accepted_contexts = context.mode in [u.OBJECT_MODES.OBJECT]
        export_sets = get_export_sets()

        batch_sets = [export_set for export_set in export_sets if export_set.consider_batch_export]

        sets_with_object_sets_export = [
            export_set
            for export_set in batch_sets
            if export_set.use_object_sets and export_set.get_selected_object_sets()
        ]
        has_selection = u.get_selected_objects()
        sets_with_selection_export = [
            export_set for export_set in batch_sets if not export_set.use_object_sets and has_selection
        ]

        return all(
            [accepted_contexts and export_sets and any([sets_with_object_sets_export, sets_with_selection_export])]
        )

    def execute(self, context):
        addon_export_props = u.get_addon_export_props()
        export_sets = u.get_export_sets()

        batch = [(idx, export_set) for idx, export_set in enumerate(export_sets) if export_set.consider_batch_export]

        exported = set()
        failures = set()

        viewport_was_local = u.is_viewport_local()
        # TODO: Collect visible objects so when we isolate again
        # they also remain visible
        if viewport_was_local:
            u.toggle_viewport_local_mode()

        for index, export_set in batch:
            object_set_names = ",".join(export_set.get_selected_object_sets())

            # Check if it has export directory
            if not export_set.export_path:
                failures.add(export_set.name)
                self.report({"WARNING"}, f"Export Set '{export_set.name}' does not have export path")
                continue

            try:
                success = bpy.ops.r0tools.quick_export_objects(
                    mkdirs_if_not_exist=addon_export_props.mkdirs_if_not_exist,
                    object_set_names=object_set_names,
                    export_entry_index=index,
                )
                if success in (True, {"FINISHED"}):
                    exported.add(export_set.name)
                else:
                    failures.add(export_set.name)
            except Exception as e:
                print(f"[ERROR] [{_mod}]: {e}")
                failures.add(export_set.name)

        if viewport_was_local:
            u.toggle_viewport_local_mode()

        self.report({"INFO"}, f"Successfully exported {len(exported)} sets: {', '.join(exported)}")

        # If failures, show last for clarity
        if failures:
            self.report({"WARNING"}, f"Failed: {', '.join(failures)}")

            self.report({"WARNING"}, f"Unable to export {len(exported)} sets. See console for details.")

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
    SimpleToolbox_OT_BatchExportObjects,
]
# fmt: on


def register():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
