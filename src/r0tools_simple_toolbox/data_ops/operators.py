import math
import time

import bmesh
import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)

from .. import utils as u

_mod = "DATA_OPS.OPERATORS"


class SimpleToolbox_OT_EdgeDataToVertexColour(bpy.types.Operator):
    bl_label = "Edge Data to Vertex Colours"
    bl_idname = "r0tools.edge_data_to_vertex_colours"
    bl_description = (
        "Convert Edge Data to Vertex Colours.\nAvailable Edge Data to convert:\n- Edge Bevel Weight.\n- Edge Creases"
    )
    bl_options = {"REGISTER", "UNDO"}

    bevel_weights_to_vcol: BoolProperty(
        name="Convert Bevel Weights", description="Convert Edge Bevel Weights to a Color Attribute"
    )  # type: ignore

    crease_to_vcol: BoolProperty(
        name="Convert Creases", description="Convert Edge Creases to a Color Attribute"
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        addon_edge_data_props = u.get_addon_edge_data_props()

        apply_as_bevel_weight = addon_edge_data_props.apply_as_bevel_weights
        apply_as_crease = addon_edge_data_props.apply_as_creases

        return u.get_selected_objects(context) and any([apply_as_bevel_weight, apply_as_crease])

    def invoke(self, context, event):
        addon_edge_data_props = u.get_addon_edge_data_props()

        self.bevel_weights_to_vcol = addon_edge_data_props.bevel_weights_to_vcol
        self.crease_to_vcol = addon_edge_data_props.crease_to_vcol

        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.prop(self, "bevel_weights_to_vcol", toggle=True)
        row.prop(self, "crease_to_vcol", toggle=True)

    def execute(self, context):
        addon_edge_data_props = u.get_addon_edge_data_props()

        # Update addon properties based on selection
        addon_edge_data_props.bevel_weights_to_vcol = self.bevel_weights_to_vcol
        addon_edge_data_props.crease_to_vcol = self.crease_to_vcol

        vcol_bevel_layer_name = addon_edge_data_props.vcol_bevel_layer_name
        vcol_crease_layer_name = addon_edge_data_props.vcol_crease_layer_name

        start_time = time.time()

        ### Progress Bar ###
        wm = context.window_manager
        total_objects = len(u.get_selected_objects(context))
        total_processed = 0
        wm.progress_begin(0, total_objects)

        for obj in u.iter_scene_objects(selected=True, types=u.OBJECT_TYPES.MESH):
            if not any([self.bevel_weights_to_vcol, self.crease_to_vcol]):
                wm.progress_end()
                return {"CANCELLED"}

            mesh = obj.data

            if obj.mode == u.OBJECT_MODES.EDIT:
                bm = bmesh.from_edit_mesh(mesh)
            else:
                bm = bmesh.new()
                bm.from_mesh(mesh)

            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            # Get Bevel/Crease Edge Attributes
            edge_bevel_layer = u.bmesh_get_bevel_weight_edge_layer(bm)
            crease_layer = u.bmesh_get_crease_layer(bm)

            # Create or get vertex color layers in bmesh
            if self.bevel_weights_to_vcol:
                bevel_vcol_layer = bm.loops.layers.color.get(vcol_bevel_layer_name)
                if not bevel_vcol_layer:
                    bevel_vcol_layer = bm.loops.layers.color.new(vcol_bevel_layer_name)

            if self.crease_to_vcol:
                crease_vcol_layer = bm.loops.layers.color.get(vcol_crease_layer_name)
                if not crease_vcol_layer:
                    crease_vcol_layer = bm.loops.layers.color.new(vcol_crease_layer_name)

            # Calculate vertex values by averaging connected edge values
            vertex_bevel_values = {}
            vertex_crease_values = {}

            for vert in bm.verts:
                connected_edges = vert.link_edges

                if connected_edges:
                    if self.bevel_weights_to_vcol:
                        if edge_bevel_layer:
                            # Only consider edges with bevel values > 0
                            edges_with_bevel = [
                                edge[edge_bevel_layer] for edge in connected_edges if edge[edge_bevel_layer] > 0
                            ]
                            if edges_with_bevel:
                                bevel_average = sum(edges_with_bevel) / len(edges_with_bevel)
                                vertex_bevel_values[vert.index] = max(0.0, min(1.0, bevel_average))
                            else:
                                vertex_bevel_values[vert.index] = 0.0
                        else:
                            vertex_bevel_values[vert.index] = 0.0

                    if self.crease_to_vcol:
                        if crease_layer:
                            # Only consider edges with crease values > 0
                            edges_with_crease = [
                                edge[crease_layer] for edge in connected_edges if edge[crease_layer] > 0
                            ]
                            if edges_with_crease:
                                crease_average = sum(edges_with_crease) / len(edges_with_crease)
                                vertex_crease_values[vert.index] = max(0.0, min(1.0, crease_average))
                            else:
                                vertex_crease_values[vert.index] = 0.0
                        else:
                            vertex_crease_values[vert.index] = 0.0
                else:
                    if self.crease_to_vcol:
                        vertex_crease_values[vert.index] = 0.0
                    if self.bevel_weights_to_vcol:
                        vertex_bevel_values[vert.index] = 0.0

            # Apply values to loops
            # Vertex Colors are stored per face corner
            for face in bm.faces:
                for loop in face.loops:
                    vert_idx = loop.vert.index
                    if self.bevel_weights_to_vcol:
                        bevel_value = vertex_bevel_values.get(vert_idx, 0.0)
                        # Grayscale
                        loop[bevel_vcol_layer] = (bevel_value, bevel_value, bevel_value, 1.0)

                    if self.crease_to_vcol:
                        crease_value = vertex_crease_values.get(vert_idx, 0.0)
                        # Grayscale
                        loop[crease_vcol_layer] = (crease_value, crease_value, crease_value, 1.0)

            if obj.mode == u.OBJECT_MODES.EDIT:
                bmesh.update_edit_mesh(mesh)
            else:
                bm.to_mesh(mesh)
                bm.free()

            # Set Bevel layer as active
            if self.bevel_weights_to_vcol:
                bpy.ops.r0tools.select_vcol_layer(select_bevel_layer=True)
            # Set Crease layer as active
            elif self.crease_to_vcol:
                bpy.ops.r0tools.select_vcol_layer(select_crease_layer=True)

            total_processed += 1
            wm.progress_update(total_processed)

        wm.progress_end()
        end_time = time.time()
        total_time = end_time - start_time
        duration_msg = f"Finished. Took {total_time:.4f} seconds."

        u.LOG(f"EdgeDataToVertexColour: {duration_msg}")
        self.report({"INFO"}, duration_msg)

        return {"FINISHED"}


class SimpleToolbox_OT_SelectEdgesWithValue(bpy.types.Operator):
    bl_label = "Select Edges With Value"
    bl_idname = "r0tools.edge_data_select_edges_with_value"
    bl_description = "Select edges with bevel weight or creases with a determined value"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.EDIT_MESH]

    value_to_select: FloatProperty(default=0.0)  # type: ignore

    select_bweights: BoolProperty(default=True)  # type: ignore
    select_creases: BoolProperty(default=False)  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def execute(self, context):
        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            bm = bmesh.from_edit_mesh(obj.data)

            bm.edges.ensure_lookup_table()

            edge_bevel_layer = u.bmesh_get_bevel_weight_edge_layer(bm)
            crease_layer = u.bmesh_get_crease_layer(bm)

            active_edge = None

            for edge in bm.edges:
                should_select = False

                if self.select_bweights and edge_bevel_layer:
                    bweight_value = edge[edge_bevel_layer]
                    if math.isclose(bweight_value, self.value_to_select):
                        should_select = True

                if self.select_creases and crease_layer:
                    crease_value = edge[crease_layer]
                    if math.isclose(crease_value, self.value_to_select):
                        should_select = True

                # Update edge selection state
                if edge.select != should_select:
                    edge.select = should_select

                    if should_select and not active_edge:
                        active_edge = edge

            if active_edge:
                bm.select_history.clear()
                bm.select_history.add(edge)

            bmesh.update_edit_mesh(obj.data)

        return {"FINISHED"}


class SimpleToolbox_OT_ApplyBWeightPreset(bpy.types.Operator):
    bl_label = "Apply"
    bl_idname = "r0tools.apply_selected_bweight_value_preset"
    bl_description = "Apply selected Edge Bevel Weight value preset to selected edges.\n\nMODIFIERS:\n- SHIFT: Select bevel weighted edges with value.\n- CTRL: Select creased edges with value"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.EDIT_MESH]
    preset_index: IntProperty(default=-1)  # type: ignore
    value: FloatProperty(default=-1.0)  # type: ignore

    select_instead: BoolProperty(default=False)  # type: ignore

    select_bweights: BoolProperty(default=False)  # type: ignore
    select_creases: BoolProperty(default=False)  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def invoke(self, context, event):
        self.select_instead = False  # Always reset
        self.select_bweights = False  # Always reset
        self.select_creases = False  # Always reset

        if event.shift:
            self.select_instead = True
            self.select_bweights = True
            self.select_creases = False
        elif event.ctrl:
            self.select_instead = True
            self.select_bweights = False
            self.select_creases = True

        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        if self.select_instead:
            layout.label(text="Select: ")
        else:
            layout.label(text="Apply: ")
        layout.prop(self, "value", text="Value")

    def execute(self, context):
        addon_edge_data_props = u.get_addon_edge_data_props()

        apply_as_bevel_weight = addon_edge_data_props.apply_as_bevel_weights
        apply_as_crease = addon_edge_data_props.apply_as_creases

        value = -1

        # Prioritise `value`
        if self.value >= 0:
            value = self.value
        elif self.preset_index >= 0:
            # Ensure index is not out of bounds
            presets = addon_edge_data_props.edge_bweight_presets.presets
            if self.preset_index < len(presets):
                value = presets[self.preset_index].value
            else:
                self.report({"ERROR", f"Preset index {self.preset_index} is out of range."})
                return {"CANCELLED"}

        # Exit if we still don't have a valid value
        if value < 0:
            self.report({"INFO"}, "No value or preset specified.")
            return {"FINISHED"}

        if self.select_instead:
            if 0 <= value <= 1:
                # fmt: off
                bpy.ops.r0tools.edge_data_select_edges_with_value(
                    value_to_select=value,
                    select_bweights=self.select_bweights,
                    select_creases=self.select_creases
                )
                # fmt: on
            else:
                return {"CANCELLED"}
        else:
            for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
                bm = bmesh.from_edit_mesh(obj.data)

                bm.edges.ensure_lookup_table()

                crease_layer = u.bmesh_get_crease_layer(bm)
                edge_bevel_layer = u.bmesh_get_bevel_weight_edge_layer(bm)

                if not edge_bevel_layer:
                    edge_bevel_layer = u.bmesh_new_bevel_weight_edge_layer(bm)

                if not crease_layer:
                    crease_layer = u.bmesh_new_crease_layer(bm)

                for edge in bm.edges:
                    if edge.select:
                        if apply_as_bevel_weight:
                            edge[edge_bevel_layer] = value

                        if apply_as_crease:
                            edge[crease_layer] = value

                bmesh.update_edit_mesh(obj.data)

        return {"FINISHED"}


class SimpleToolbox_OT_SelectColourAttributeLayer(bpy.types.Operator):
    bl_label = "Select Colour Attribute Layer"
    bl_idname = "r0tools.select_vcol_layer"
    bl_description = "Which colour attribute layer to select"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    select_bevel_layer: BoolProperty(default=False, name="Select Bevel Layer", description="Select Bevel Layer")  # type: ignore
    select_crease_layer: BoolProperty(default=False, name="Select Crease Layer", description="Select Crease Layer")  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.prop(self, "select_bevel_layer", toggle=True)
        row.prop(self, "select_crease_layer", toggle=True)

    def execute(self, context):
        addon_edge_data_props = u.get_addon_edge_data_props()

        bevel_layer_name = addon_edge_data_props.vcol_bevel_layer_name
        crease_layer_name = addon_edge_data_props.vcol_crease_layer_name

        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            mesh = obj.data

            if obj.mode == u.OBJECT_MODES.EDIT:
                bm = bmesh.from_edit_mesh(mesh)
            else:
                bm = bmesh.new()
                bm.from_mesh(mesh)

            # Get Bevel/Crease Edge Attributes
            edge_bevel_layer = u.bmesh_get_bevel_weight_edge_layer(bm)
            crease_layer = u.bmesh_get_crease_layer(bm)

            # Set Bevel layer as active
            if self.select_bevel_layer:
                vcol_bevel_attribute_layer = mesh.color_attributes.get(bevel_layer_name)
                if edge_bevel_layer:
                    mesh.color_attributes.active_color = vcol_bevel_attribute_layer
                # bpy.ops.geometry.color_attribute_render_set(name="Bevel")

                self.report({"INFO"}, "Selected Bevel Colour Attribute Layer")

            # Set Crease layer as active
            elif self.select_crease_layer:
                vcol_crease_attribute_layer = mesh.color_attributes.get(crease_layer_name)
                if crease_layer:
                    mesh.color_attributes.active_color = vcol_crease_attribute_layer

                self.report({"INFO"}, "Selected Crease Colour Attribute Layer")

        return {"FINISHED"}


# fmt: off
classes = [
    SimpleToolbox_OT_EdgeDataToVertexColour,
    SimpleToolbox_OT_ApplyBWeightPreset,
    SimpleToolbox_OT_SelectEdgesWithValue,
    SimpleToolbox_OT_SelectColourAttributeLayer
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
