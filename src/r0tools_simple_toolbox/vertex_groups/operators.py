import bmesh
import bpy
from bpy.props import BoolProperty, FloatVectorProperty, IntProperty, StringProperty

from .. import utils as u
from .vertex_groups import *

_mod = "VERTEX_GROUPS.OPERATORS"


class SimpleToolbox_OT_VgroupsAddPopup(bpy.types.Operator):
    bl_idname = "r0tools.vgrups_add_popup"
    bl_label = "Add Vertex Group"
    bl_description = "Adds a named Vertex Group to all selected objects"
    bl_options = {"REGISTER", "UNDO"}

    _default_name = "Vertex Group"
    vertex_group_name: StringProperty(name="Name", default=_default_name)  # type: ignore

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]
    accepted_object_types = [u.OBJECT_TYPES.MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def invoke(self, context, event):
        # Reset Name
        self.vertex_group_name = self._default_name

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        split = row.split(factor=0.9)
        split.prop(self, "vertex_group_name")

    def execute(self, context):
        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            vertex_group_add(obj, self.vertex_group_name)

        return {"FINISHED"}


class SimpleToolbox_OT_VgroupsRemoveHighlighted(bpy.types.Operator):
    bl_idname = "r0tools.vgrups_remove_highlighted"
    bl_label = "Remove Highlighted Vertex Group. Respects locks an dwill not override them."
    bl_description = "Removes the currently highlighted Vertex Group in the list."
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]
    accepted_object_types = [u.OBJECT_TYPES.MESH]

    @classmethod
    def poll(cls, context):
        accepted_context = context.mode in cls.accepted_contexts
        has_selection = len(context.selected_objects) > 0
        has_vgroups = get_vertex_groups_count() > 0

        return accepted_context and has_selection and has_vgroups

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        index = get_active_vertex_group_index()
        highlighted = get_vertex_groups()[index]

        highlighted_name = highlighted.name
        highlighted_locked = highlighted.locked

        if highlighted_locked:
            self.report({"WARNING"}, f"Group '{highlighted_name}' is locked.")
            return {"FINISHED"}

        total_removed = 0

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            vgroups = obj.vertex_groups

            for vgroup in reversed(vgroups):
                vgroup_name = vgroup.name

                if vgroup_name == highlighted_name:
                    vgroups.remove(vgroup)
                    total_removed += 1

        self.report({"INFO"}, f"Removed {total_removed} Vertex Groups.")

        return {"FINISHED"}


class SimpleToolbox_OT_RemoveUnusedVertexGroups(bpy.types.Operator):
    bl_idname = "r0tools.remove_unused_vertex_groups"
    bl_label = "Remove Unused Vertex Groups"
    bl_description = "Removes unused Vertex Groups across all selected objects"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]
    accepted_object_types = [u.OBJECT_TYPES.MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and len(context.selected_objects) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        if u.IS_DEBUG():
            print("\n------------- Remove Unused Materials -------------")

        original_active = u.get_active_object()

        total_removed: int = 0

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            # Set active object
            u.set_active_object(obj)

            used_group_indices = set()
            obj_data = obj.data

            for vert in obj_data.vertices:
                for vg in vert.groups:
                    # Only iterates groups that are used
                    # Is weight check needed? vg.weight > 0?
                    used_group_indices.add(vg.group)  # This is an index

            before_count = len(obj.vertex_groups)  # Used for reporting later

            # Locked vertex groups from UIList. Prevent removal of locked groups.
            locked_vertex_groups = [vgroup.name for vgroup in get_vertex_groups() if vgroup.locked]

            for group in reversed(obj.vertex_groups):
                if group.index not in used_group_indices and group.name not in locked_vertex_groups:
                    obj.vertex_groups.remove(group)

            total_removed += before_count - len(obj.vertex_groups)

        self.report({"INFO"}, f"Removed {total_removed} Vertex Groups.")

        u.set_active_object(original_active)

        return {"FINISHED"}


class SimpleToolbox_OT_VgroupsRemoveSelected(bpy.types.Operator):
    bl_idname = "r0tools.vgroups_remove_selected"
    bl_label = "Remove Selected"
    bl_description = "Removes, from all selected objects, the corresponding selected vertex groups"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]
    accepted_object_types = [u.OBJECT_TYPES.MESH]

    @classmethod
    def poll(cls, context):
        accepted_context = context.mode in cls.accepted_contexts
        has_vgroups = get_vertex_groups_count() > 0

        return accepted_context and has_vgroups

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        # Get selected vertex groups
        total_removed = 0

        # Find selected properties to remove
        vgroups_names_to_remove = u.get_selected_vgroups_names()
        highlighted_vg_entry = get_vertex_group_at_index(get_active_vertex_group_index())

        if highlighted_vg_entry is not None:
            highlighted_vg_entry = highlighted_vg_entry.name
        else:
            return {"FINISHED"}

        if len(vgroups_names_to_remove) < 1:
            # If nothing is checked (selected), use current highlighted item as selection
            vgroups_names_to_remove = [highlighted_vg_entry]

        locked_vertex_groups_names = [item.name for item in u.get_vertex_groups() if item.locked]

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            vgroups = obj.vertex_groups

            for vgroup in reversed(vgroups):
                vgroup_name = vgroup.name
                locked = vgroup_name in locked_vertex_groups_names

                if vgroup_name in vgroups_names_to_remove and not locked:
                    vgroups.remove(vgroup)
                    total_removed += 1

        self.report({"INFO"}, f"Removed {total_removed} Vertex Groups.")

        return {"FINISHED"}


class SimpleToolbox_OT_VgroupsKeepSelected(bpy.types.Operator):
    bl_idname = "r0tools.vgroups_keep_selected"
    bl_label = "Keep Selected"
    bl_description = "Keeps all selected vertex groups for selected objects while removing all others"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]
    accepted_object_types = [u.OBJECT_TYPES.MESH]

    @classmethod
    def poll(cls, context):
        accepted_context = context.mode in cls.accepted_contexts
        has_vgroups = get_vertex_groups_count() > 0

        return accepted_context and has_vgroups

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        addon_props = u.get_addon_props()

        # Get selected vertex groups
        total_removed = 0
        total_objects = 0

        # Find selected properties to remove
        vgroups_names_to_remove = u.get_selected_vgroups_names()
        highlighted_vg_entry = get_vertex_group_at_index(get_active_vertex_group_index())

        if highlighted_vg_entry is not None:
            highlighted_vg_entry = highlighted_vg_entry.name
        else:
            return {"FINISHED"}

        if len(vgroups_names_to_remove) < 1:
            # If nothing is checked (selected), use current highlighted item as selection
            vgroups_names_to_remove = [highlighted_vg_entry]

        locked_vertex_groups_names = [item.name for item in u.get_vertex_groups() if item.locked]

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            vgroups = obj.vertex_groups

            for vgroup in reversed(vgroups):
                vgroup_name = vgroup.name
                locked = vgroup_name in locked_vertex_groups_names

                if vgroup_name not in vgroups_names_to_remove and not locked:
                    vgroups.remove(vgroup)
                    total_removed += 1

        self.report({"INFO"}, f"Removed {total_removed} Vertex Groups.")

        return {"FINISHED"}


class SimpleToolbox_OT_VgroupsSelectObjectsWithVgroups(bpy.types.Operator):
    bl_idname = "r0tools.selected_objects_with_selected_vgroups"
    bl_label = "Select Objects w/ Vertex Groups"
    bl_description = "From currently selected objects, selects all objects that contain the selected Vertex Groups"
    bl_options = {"REGISTER", "UNDO"}

    accepted_object_types = [u.OBJECT_TYPES.MESH]

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT and len(context.selected_objects) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        selected_vertex_groups_names = u.get_selected_vgroups_names()
        highlighted_vg_entry = get_vertex_group_at_index(get_active_vertex_group_index())

        if highlighted_vg_entry is not None:
            highlighted_vg_entry = highlighted_vg_entry.name
        else:
            return {"FINISHED"}

        if len(selected_vertex_groups_names) < 1:
            # If nothing is checked (selected), use current highlighted item as selection
            selected_vertex_groups_names = [highlighted_vg_entry]

        objects_to_select = []

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            vgroups = obj.vertex_groups

            for vgroup in vgroups:
                vgroup_name = vgroup.name

                if vgroup_name in selected_vertex_groups_names:
                    objects_to_select.append(obj)
                    break

        if objects_to_select:
            u.set_vertex_groups_depsgraph_do_update(False)
            u.deselect_all()
            for obj in objects_to_select:
                u.select_object(obj)

            u.set_active_object(objects_to_select[0])

        u.set_vertex_groups_depsgraph_do_update(True)

        return {"FINISHED"}


class SimpleToolbox_OT_VgroupsAssignVertices(bpy.types.Operator):
    bl_idname = "r0tools.vgroups_assign_vertices"
    bl_label = "Assign"
    bl_description = "Assigns selected vertices to selected Vertex Groups"
    bl_options = {"REGISTER", "UNDO"}

    accepted_object_types = [u.OBJECT_TYPES.MESH]

    def execute(self, context):
        # Selected vertex groups
        selected_vgroups_names = get_selected_vgroups_names()
        highlighted_vg_entry = get_vertex_group_at_index(get_active_vertex_group_index())

        if highlighted_vg_entry is not None:
            highlighted_vg_entry = highlighted_vg_entry.name
        else:
            return {"FINISHED"}

        if len(selected_vgroups_names) < 1:
            # If nothing is checked (selected), use current highlighted item as selection
            selected_vgroups_names = [highlighted_vg_entry]

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            # Set it as active
            u.set_active_object(obj)

            select_mode = u.get_selection_mode()
            has_selection = False

            # Get the bmesh
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            if select_mode == 0:  # Vertices
                for v in bm.verts:
                    if v.select:
                        has_selection = True
                        break
            elif select_mode == 1:  # Edges
                for e in bm.edges:
                    if e.select:
                        has_selection = True
                        break
            elif select_mode == 2:  # Faces
                for f in bm.faces:
                    if f.select:
                        has_selection = True
                        break
            else:
                continue

            # Selected vertices
            # selected_verts_index = [v.index for v in bm.verts if v.select]

            if not has_selection:
                continue

            # Add the group(s) they don't exist
            for vgroup_name in selected_vgroups_names:
                vertex_group_add(obj, vgroup_name)

            # Now for each selected name, select it at the object vgroup index
            for vertex_group in iter_obj_vertex_groups(obj):
                if vertex_group.name in selected_vgroups_names:
                    if set_obj_active_vertex_group_index(obj, vertex_group):
                        # Let's try to use the built-in function
                        bpy.ops.object.vertex_group_assign()

                        # Add vertices to the vertex group. Does not work in edit mode for some reason...
                        # vertex_group.add(selected_verts_index, 1.0, "ADD")

        return {"FINISHED"}


class SimpleToolbox_OT_VgroupsUnassignVertices(bpy.types.Operator):
    bl_idname = "r0tools.vgroups_unassign_vertices"
    bl_label = "Unassign"
    bl_description = "Unassigns selected vertices from selected Vertex Groups"
    bl_options = {"REGISTER", "UNDO"}

    accepted_object_types = [u.OBJECT_TYPES.MESH]

    def execute(self, context):
        # Selected vertex groups
        selected_vgroups_names = get_selected_vgroups_names()
        highlighted_vg_entry = get_vertex_group_at_index(get_active_vertex_group_index())

        if highlighted_vg_entry is not None:
            highlighted_vg_entry = highlighted_vg_entry.name
        else:
            return {"FINISHED"}

        if len(selected_vgroups_names) < 1:
            # If nothing is checked (selected), use current highlighted item as selection
            selected_vgroups_names = [highlighted_vg_entry]

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            # Set it as active
            u.set_active_object(obj)

            for vertex_group in iter_obj_vertex_groups(obj):
                if vertex_group.name in selected_vgroups_names:
                    if set_obj_active_vertex_group_index(obj, vertex_group):
                        # Let's try to use the built-in function
                        bpy.ops.object.vertex_group_remove_from()

        return {"FINISHED"}


class SimpleToolbox_OT_VgroupsSelectVertices(bpy.types.Operator):
    bl_idname = "r0tools.vgroups_select_vertices"
    bl_label = "Select"
    bl_description = "Selects the vertices assign to the selected Vertex Group(s)"
    bl_options = {"REGISTER", "UNDO"}

    accepted_object_types = [u.OBJECT_TYPES.MESH]

    def execute(self, context):
        # Selected vertex groups
        selected_vgroups_names = get_selected_vgroups_names()
        highlighted_vg_entry = get_vertex_group_at_index(get_active_vertex_group_index())

        if highlighted_vg_entry is not None:
            highlighted_vg_entry = highlighted_vg_entry.name
        else:
            return {"FINISHED"}

        if len(selected_vgroups_names) < 1:
            # If nothing is checked (selected), use current highlighted item as selection
            selected_vgroups_names = [highlighted_vg_entry]

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            # Set it as active
            u.set_active_object(obj)

            for vertex_group in iter_obj_vertex_groups(obj):
                if vertex_group.name in selected_vgroups_names:
                    if set_obj_active_vertex_group_index(obj, vertex_group):
                        # Let's try to use the built-in function
                        bpy.ops.object.vertex_group_select()

        return {"FINISHED"}


class SimpleToolbox_OT_VgroupsDeselectVertices(bpy.types.Operator):
    bl_idname = "r0tools.vgroups_deselect_vertices"
    bl_label = "Deselect"
    bl_description = "Deselects the vertices assign to the selected Vertex Group(s)"
    bl_options = {"REGISTER", "UNDO"}

    accepted_object_types = [u.OBJECT_TYPES.MESH]

    def execute(self, context):
        # Selected vertex groups
        selected_vgroups_names = get_selected_vgroups_names()
        highlighted_vg_entry = get_vertex_group_at_index(get_active_vertex_group_index())

        if highlighted_vg_entry is not None:
            highlighted_vg_entry = highlighted_vg_entry.name
        else:
            return {"FINISHED"}

        if len(selected_vgroups_names) < 1:
            # If nothing is checked (selected), use current highlighted item as selection
            selected_vgroups_names = [highlighted_vg_entry]

        for obj in u.iter_scene_objects(selected=True, types=self.accepted_object_types):
            # Set it as active
            u.set_active_object(obj)

            for vertex_group in iter_obj_vertex_groups(obj):
                if vertex_group.name in selected_vgroups_names:
                    if set_obj_active_vertex_group_index(obj, vertex_group):
                        # Let's try to use the built-in function
                        bpy.ops.object.vertex_group_deselect()

        return {"FINISHED"}


# fmt: off
classes = [
    SimpleToolbox_OT_VgroupsAddPopup,
    SimpleToolbox_OT_VgroupsRemoveHighlighted,
    SimpleToolbox_OT_RemoveUnusedVertexGroups,
    SimpleToolbox_OT_VgroupsRemoveSelected,
    SimpleToolbox_OT_VgroupsKeepSelected,
    SimpleToolbox_OT_VgroupsSelectObjectsWithVgroups,
    SimpleToolbox_OT_VgroupsAssignVertices,
    SimpleToolbox_OT_VgroupsUnassignVertices,
    SimpleToolbox_OT_VgroupsSelectVertices,
    SimpleToolbox_OT_VgroupsDeselectVertices,
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
