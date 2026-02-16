import logging
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

log = logging.getLogger(__name__)


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

    use_max_value: BoolProperty(
        name="Use Max Value",
        description="Use the highest value among connected edges instead of averaging",
        default=False,
    )  # type: ignore

    convert_to_channel_r: BoolProperty(
        name="Red", description="Apply converted values to Red vertex colour channel", default=True
    )  # type: ignore

    convert_to_channel_g: BoolProperty(
        name="Red", description="Apply converted values to Green vertex colour channel", default=False
    )  # type: ignore

    convert_to_channel_b: BoolProperty(
        name="Red", description="Apply converted values to Blue vertex colour channel", default=False
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        addon_edge_data_props = u.get_addon_edge_data_props()

        apply_as_bevel_weight = addon_edge_data_props.apply_as_bevel_weights
        apply_as_crease = addon_edge_data_props.apply_as_creases

        return u.get_selected_objects(context) and any([apply_as_bevel_weight, apply_as_crease])

    def invoke(self, context, event):
        addon_edge_data_props = u.get_addon_edge_data_props()

        self.bevel_weights_to_vcol = addon_edge_data_props.convert_data_as == "BEVEL_WEIGHTS"
        self.crease_to_vcol = addon_edge_data_props.convert_data_as == "CREASES"
        self.use_max_value = addon_edge_data_props.convert_using_max_value

        self.convert_to_channel_r = addon_edge_data_props.apply_value_to_channel_enum == "R"

        self.convert_to_channel_g = addon_edge_data_props.apply_value_to_channel_enum == "G"

        self.convert_to_channel_b = addon_edge_data_props.apply_value_to_channel_enum == "B"

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

            bevel_vcol_layer = None
            crease_vcol_layer = None

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
                                if self.use_max_value:
                                    bevel_value = max(edges_with_bevel)
                                else:
                                    bevel_value = sum(edges_with_bevel) / len(edges_with_bevel)
                                vertex_bevel_values[vert.index] = max(0.0, min(1.0, bevel_value))
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
                                if self.use_max_value:
                                    crease_value = max(edges_with_crease)
                                else:
                                    crease_value = sum(edges_with_crease) / len(edges_with_crease)
                                vertex_crease_values[vert.index] = max(0.0, min(1.0, crease_value))
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

                        existing_color = loop[bevel_vcol_layer]

                        # Apply values to RGB channels
                        bevel_value_r = bevel_value if self.convert_to_channel_r else existing_color[0]
                        bevel_value_g = bevel_value if self.convert_to_channel_g else existing_color[1]
                        bevel_value_b = bevel_value if self.convert_to_channel_b else existing_color[2]

                        loop[bevel_vcol_layer] = (bevel_value_r, bevel_value_g, bevel_value_b, 1.0)

                    if self.crease_to_vcol:
                        crease_value = vertex_crease_values.get(vert_idx, 0.0)

                        existing_color = loop[crease_vcol_layer]

                        # Apply values to RGB channels
                        crease_value_r = crease_value if self.convert_to_channel_r else existing_color[0]
                        crease_value_g = crease_value if self.convert_to_channel_g else existing_color[1]
                        crease_value_b = crease_value if self.convert_to_channel_b else existing_color[2]

                        loop[crease_vcol_layer] = (crease_value_r, crease_value_g, crease_value_b, 1.0)

            # Allow bmesh to update to prevent decode errors
            if obj.mode == u.OBJECT_MODES.EDIT:
                bmesh.update_edit_mesh(mesh)
            else:
                bm.to_mesh(mesh)

            bm.free()

            total_processed += 1
            wm.progress_update(total_processed)

        # Set Bevel layer as active
        if self.bevel_weights_to_vcol:
            bpy.ops.r0tools.select_vcol_layer(select_bevel_layer=True)
        # Set Crease layer as active
        elif self.crease_to_vcol:
            bpy.ops.r0tools.select_vcol_layer(select_crease_layer=True)

        wm.progress_end()
        end_time = time.time()
        total_time = end_time - start_time
        duration_msg = f"Finished. Took {total_time:.4f} seconds."

        log.info(f"EdgeDataToVertexColour: {duration_msg}")
        self.report({"INFO"}, duration_msg)

        return {"FINISHED"}


class SimpleToolbox_OT_SelectEdgesWithValue(bpy.types.Operator):
    bl_label = "Select Edges With Value"
    bl_idname = "r0tools.edge_data_select_edges_with_value"
    bl_description = "Select Edges with Bevel Weight or Creases with the determined assigned value"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.EDIT_MESH]

    value_to_select: FloatProperty(default=0.0)  # type: ignore

    select_bweights: BoolProperty(default=True)  # type: ignore
    select_creases: BoolProperty(default=False)  # type: ignore

    @classmethod
    def description(cls, context, properties):
        value = round(properties.value_to_select, 2)

        if value == 0.0:
            return f"Select all Sharp Edges that have no Bevel Weight or Crease value assigned"

        return f"Select all Edges with Bevel Weight or Creases have an assigned value of {value}"

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def execute(self, context):
        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            bm = bmesh.from_edit_mesh(obj.data)

            bm.edges.ensure_lookup_table()

            edge_bevel_layer = u.bmesh_get_bevel_weight_edge_layer(bm)
            crease_layer = u.bmesh_get_crease_layer(bm)

            if not edge_bevel_layer:
                edge_bevel_layer = u.bmesh_new_bevel_weight_edge_layer(bm)

            if not crease_layer:
                crease_layer = u.bmesh_new_crease_layer(bm)

            active_edge = None

            for edge in bm.edges:
                should_select = False

                # Edge-case: Select 0%
                # Selecting with 0% makes no sense without a specific context because
                # it would select all edges with no bevel edge weight.
                # It would make more sense to only select edges with 0% that are also sharp edges.
                zero_edge_case = math.isclose(self.value_to_select, 0)

                if self.select_bweights and edge_bevel_layer:
                    bweight_value = edge[edge_bevel_layer]
                    if math.isclose(bweight_value, self.value_to_select):
                        # Edge-case: 0%
                        if zero_edge_case:
                            should_select = not edge.smooth
                        else:
                            should_select = True

                if self.select_creases and crease_layer:
                    crease_value = edge[crease_layer]
                    if math.isclose(crease_value, self.value_to_select):
                        # Edge-case: 0%
                        if zero_edge_case:
                            should_select = not edge.smooth
                        else:
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


class SimpleToolbox_OT_ApplyEdgeDataValuePreset(bpy.types.Operator):
    bl_label = "Apply"
    bl_idname = "r0tools.apply_selected_edge_data_value_preset"
    bl_description = "Apply selected Edge Bevel Weight value preset to selected edges.\n\nMODIFIERS:\n- SHIFT: Select bevel weighted edges with value.\n- CTRL: Select creased edges with value"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.EDIT_MESH]
    preset_index: IntProperty(default=-1)  # type: ignore
    value: FloatProperty(default=-1.0)  # type: ignore

    select_instead: BoolProperty(default=False)  # type: ignore

    select_bweights: BoolProperty(default=False)  # type: ignore
    select_creases: BoolProperty(default=False)  # type: ignore

    @classmethod
    def description(cls, context, properties):
        value = round(properties.value, 2)

        if value == 0.0:
            return f"Apply selected Edge Bevel Weight value of {value} to selected edges.\n\n++SPECIAL CASE++: Selecting edges with a value of 0 will instead select ALL Sharp Edges that have no Bevel Weight or Crease value assigned to them.\n\nMODIFIERS:\n- SHIFT: Select all Sharp Edges that have no Bevel Weight value assigned.\n- CTRL: Select all Sharp Edges that have no Crease value assigned."

        return f"Apply selected Edge Bevel Weight or Crease value of {value} to selected edges.\n\nMODIFIERS:\n- SHIFT: Select Bevel Weighted edges with value {value}.\n- CTRL: Select Creased edges with value {value}"

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
            presets = addon_edge_data_props.edge_bweights_presets.presets
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


class SimpleToolbox_OT_ApplyEdgeDataValueFromActiveEdge(bpy.types.Operator):
    bl_label = "Apply from Active Edge"
    bl_idname = "r0tools.apply_edge_data_value_from_active_edge"
    bl_description = (
        "Applies to all selected edges the data value (edge bevel weight or crease) from the active selected edge"
    )
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def execute(self, context):
        addon_edge_data_props = u.get_addon_edge_data_props()

        source_value = None
        source_found = False
        source_layer = None

        apply_as_bevel_weight = addon_edge_data_props.apply_as_bevel_weights
        apply_as_crease = addon_edge_data_props.apply_as_creases

        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            # Create bmesh representation for each
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            active_element = bm.select_history.active

            # Check if the active element is an edge
            if active_element and isinstance(active_element, bmesh.types.BMEdge):
                if apply_as_bevel_weight:
                    layer = u.bmesh_get_bevel_weight_edge_layer(bm)
                    if layer is None:
                        continue
                    source_value = active_element[layer]
                elif apply_as_crease:
                    layer = u.bmesh_get_crease_layer(bm)
                    if layer is None:
                        continue
                    source_value = active_element[layer]

                source_found = True
                source_layer = layer
                break

        if not source_layer:
            self.report({"WARNING"}, "Data layer not present in object with active edge. Assign a value first.")
            return {"CANCELLED"}

        if not source_found:
            self.report({"WARNING"}, "No active edge found in selection")
            return {"CANCELLED"}

        if not any([apply_as_bevel_weight, apply_as_crease]):
            return {"CANCELLED"}

        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            # Create bmesh representation for each
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()

            if apply_as_bevel_weight:
                get_layer = u.bmesh_get_bevel_weight_edge_layer
                new_layer = u.bmesh_new_bevel_weight_edge_layer
            elif apply_as_crease:
                get_layer = u.bmesh_get_crease_layer
                new_layer = u.bmesh_new_crease_layer

            layer = get_layer(bm)
            if layer is None:
                layer = new_layer(bm)

            for edge in bm.edges:
                if edge.select:
                    edge[layer] = source_value

            bmesh.update_edit_mesh(obj.data)

        return {"FINISHED"}


class SimpleToolbox_OT_SelectEdgeDataValueFromActiveEdge(bpy.types.Operator):
    bl_label = "Select from Active Edge"
    bl_idname = "r0tools.select_edge_data_value_from_active_edge"
    bl_description = "Selects all edges the data value (edge bevel weight or crease) from the active selected edge"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.EDIT_MESH]

    add_to_selection: BoolProperty(name="Add to selection", default=False)  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def invoke(self, context, event):
        self.add_to_selection = False  # Always reset

        if event.shift:
            self.add_to_selection = True

        return self.execute(context)

    def execute(self, context):
        addon_edge_data_props = u.get_addon_edge_data_props()

        source_value = None
        source_found = False
        source_layer = None

        apply_as_bevel_weight = addon_edge_data_props.apply_as_bevel_weights
        apply_as_crease = addon_edge_data_props.apply_as_creases

        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            # Create bmesh representation for each
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            active_element = bm.select_history.active

            # Check if the active element is an edge
            if active_element and isinstance(active_element, bmesh.types.BMEdge):
                if apply_as_bevel_weight:
                    layer = u.bmesh_get_bevel_weight_edge_layer(bm)
                    if layer is None:
                        continue
                    source_value = active_element[layer]
                elif apply_as_crease:
                    layer = u.bmesh_get_crease_layer(bm)
                    if layer is None:
                        continue
                    source_value = active_element[layer]

                source_found = True
                source_layer = layer
                break

        if not source_layer:
            self.report({"WARNING"}, "Data layer not present in object with active edge. Assign a value first.")
            return {"CANCELLED"}

        if not source_found:
            self.report({"WARNING"}, "No active edge found in selection")
            return {"CANCELLED"}

        if not any([apply_as_bevel_weight, apply_as_crease]):
            return {"CANCELLED"}

        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            # Create bmesh representation for each
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()

            # Clear selection
            if not self.add_to_selection:
                for vert in bm.verts:
                    vert.select = False
                for edge in bm.edges:
                    edge.select = False
                for face in bm.faces:
                    face.select = False

            if apply_as_bevel_weight:
                get_layer = u.bmesh_get_bevel_weight_edge_layer
            elif apply_as_crease:
                get_layer = u.bmesh_get_crease_layer

            layer = get_layer(bm)
            if layer is None:
                continue

            for edge in bm.edges:
                if math.isclose(edge[layer], source_value):
                    edge.select = True

            bm.select_flush_mode()

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

        bevel_objects_applied = 0
        crease_objects_applied = 0

        for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH]):
            mesh = obj.data

            """
            if obj.mode == u.OBJECT_MODES.EDIT:
                bm = bmesh.from_edit_mesh(mesh)
            else:
                bm = bmesh.new()
                bm.from_mesh(mesh)
            """

            # Set Bevel layer as active
            if self.select_bevel_layer:
                vcol_bevel_attribute_layer = mesh.color_attributes.get(bevel_layer_name, None)
                if vcol_bevel_attribute_layer:
                    mesh.color_attributes.active_color = vcol_bevel_attribute_layer
                    # bpy.ops.geometry.color_attribute_render_set(name="Bevel")
                    bevel_objects_applied += 1

            # Set Crease layer as active
            elif self.select_crease_layer:
                vcol_crease_attribute_layer = mesh.color_attributes.get(crease_layer_name, None)
                if vcol_crease_attribute_layer:
                    mesh.color_attributes.active_color = vcol_crease_attribute_layer
                    crease_objects_applied += 1

        if self.select_bevel_layer:
            self.report({"INFO"}, f"Selected Bevel Colour Attribute Layer for {bevel_objects_applied} Objects")

        if self.select_crease_layer:
            self.report({"INFO"}, f"Selected Crease Colour Attribute Layer for {crease_objects_applied} Objects")

        return {"FINISHED"}


# fmt: off
classes = [
    SimpleToolbox_OT_EdgeDataToVertexColour,
    SimpleToolbox_OT_ApplyEdgeDataValuePreset,
    SimpleToolbox_OT_SelectEdgesWithValue,
    SimpleToolbox_OT_ApplyEdgeDataValueFromActiveEdge,
    SimpleToolbox_OT_SelectEdgeDataValueFromActiveEdge,
    SimpleToolbox_OT_SelectColourAttributeLayer
]
# fmt: on


def register():
    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
