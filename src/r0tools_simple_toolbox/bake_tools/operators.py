import bmesh
import bpy
from bpy.props import BoolProperty, FloatVectorProperty, IntProperty, StringProperty

from .. import utils as u

_mod = "BAKE_TOOLS.OPERATORS"


class SimpleToolbox_OT_EdgeDataToVertexColour(bpy.types.Operator):
    bl_label = "Edge Data -> VCol"
    bl_idname = "r0tools.edge_data_to_vertex_colours"
    bl_description = "Convert Edge Data to Vertex Colours"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return u.get_selected_objects(context)

    def execute(self, context):
        addon_props = u.get_addon_props()

        vcol_bevel_layer_name = "Bevel"
        vcol_crease_layer_name = "Crease"

        for obj in u.iter_scene_objects(selected=True, types=u.OBJECT_TYPES.MESH):
            mesh = obj.data

            if obj.mode == "EDIT":
                bm = bmesh.from_edit_mesh(mesh)
            else:
                bm = bmesh.new()
                bm.from_mesh(mesh)

            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            # Get Bevel Edge Attributes
            crease_layer = u.bmesh_get_crease_layer(bm)
            edge_bevel_layer = u.bmesh_get_bevel_weight_edge_layer(bm)

            # Create or get vertex color layers in bmesh
            crease_vcol_layer = bm.loops.layers.color.get(vcol_crease_layer_name)
            if not crease_vcol_layer:
                crease_vcol_layer = bm.loops.layers.color.new(vcol_crease_layer_name)

            bevel_vcol_layer = bm.loops.layers.color.get(vcol_bevel_layer_name)
            if not bevel_vcol_layer:
                bevel_vcol_layer = bm.loops.layers.color.new(vcol_bevel_layer_name)

            # Calculate vertex values by averaging connected edge values
            vertex_crease_values = {}
            vertex_bevel_values = {}

            for vert in bm.verts:
                connected_edges = vert.link_edges

                if connected_edges:
                    if crease_layer:
                        # Average crease values
                        crease_sum = sum(edge[crease_layer] for edge in connected_edges)
                        crease_average = crease_sum / len(connected_edges)
                        # Clamp 0-1
                        vertex_crease_values[vert.index] = max(0.0, min(1.0, crease_average))
                    else:
                        vertex_crease_values[vert.index] = 0.0

                    if edge_bevel_layer:
                        # Average bevel values
                        bevel_sum = sum(edge[edge_bevel_layer] for edge in connected_edges)
                        bevel_average = bevel_sum / len(connected_edges)
                        # Clamp 0-1
                        vertex_bevel_values[vert.index] = max(0.0, min(1.0, bevel_average))
                    else:
                        vertex_bevel_values[vert.index] = 0.0
                else:
                    vertex_crease_values[vert.index] = 0.0
                    vertex_bevel_values[vert.index] = 0.0

            # Apply values to loops
            # Vertex Colors are stored per face corner
            for face in bm.faces:
                for loop in face.loops:
                    vert_idx = loop.vert.index
                    crease_value = vertex_crease_values.get(vert_idx, 0.0)
                    bevel_value = vertex_bevel_values.get(vert_idx, 0.0)

                    # Grayscale
                    loop[crease_vcol_layer] = (crease_value, crease_value, crease_value, 1.0)
                    loop[bevel_vcol_layer] = (bevel_value, bevel_value, bevel_value, 1.0)

            if obj.mode == "EDIT":
                bmesh.update_edit_mesh(mesh)
            else:
                bm.to_mesh(mesh)
                bm.free()

            # Set Bevel layer as active and renderable
            vcol_bevel_attribute_layer = mesh.color_attributes.get(vcol_bevel_layer_name)
            if vcol_bevel_attribute_layer:
                mesh.color_attributes.active_color = vcol_bevel_attribute_layer
                # bpy.ops.geometry.color_attribute_render_set(name="Bevel")

        return {"FINISHED"}


# fmt: off
classes = [
    SimpleToolbox_OT_EdgeDataToVertexColour
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
