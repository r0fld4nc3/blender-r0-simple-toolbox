import logging

import bmesh
import bpy
from mathutils import Vector

from .. import utils as u

THRESHOLD = 0.00001  # Minimum area for an island to be considered "too small"
THRESHOLD_PX_COVERAGE = 80.0  # The "pixel area squared", or coverage in this case, is essentially the area of the UV island expressed in pixel units rather than in UV space (which ranges from 0 to 1)
THRESHOLD_PCT = 0.000475  # Minimum pixel percentage coverage for an island to be considered "too small"
TEXTURE_SIZE_X = 4096  # Texture resolution in pixels (e.g., 4096x4096)
TEXTURE_SIZE_Y = 4096  # Texture resolution in pixels (e.g., 4096x4096)
TEXTURE_SIZE_SQ = TEXTURE_SIZE_X * TEXTURE_SIZE_Y

log = logging.getLogger(__name__)


def get_uv_islands(obj):
    """Find UV islands in an object's active UV map while correctly handling overlapping islands."""

    if not obj.data.uv_layers:
        return []

    # Enter Edit Mode and get the BMesh
    bpy.ops.object.mode_set(mode="EDIT")
    mesh = bmesh.from_edit_mesh(obj.data)

    # Ensure lookup tables are up-to-date
    mesh.faces.ensure_lookup_table()
    mesh.edges.ensure_lookup_table()
    mesh.verts.ensure_lookup_table()

    # Prepare UV connectivity dictionary with both UV coordinates and vertex indices
    uv_layer = mesh.loops.layers.uv.active
    uv_faces = {}

    for face in mesh.faces:
        uv_faces[face.index] = [
            (loop[uv_layer].uv, loop.vert.index) for loop in face.loops
        ]  # Store both UV and vertex index

    # Find connected UV islands
    islands = []
    visited = set()

    def flood_fill(face_idx, island):
        """Recursive function to collect connected faces in an island."""
        if face_idx in visited:
            return
        visited.add(face_idx)
        island.append(face_idx)

        face_data = uv_faces[face_idx]  # (UV, VertexIndex) pairs
        for edge in mesh.faces[face_idx].edges:
            for linked_face in edge.link_faces:
                if linked_face.index not in visited:
                    linked_data = uv_faces[linked_face.index]

                    # Ensure UVs match but also belong to the same vertex index (avoid accidental merging)
                    if any(
                        (uv1.xy == uv2.xy and v1 == v2)  # Ensure both UV and vertex index match
                        for (uv1, v1) in face_data
                        for (uv2, v2) in linked_data
                    ):
                        flood_fill(linked_face.index, island)

    for face_idx in uv_faces:
        if face_idx not in visited:
            island = []
            flood_fill(face_idx, island)
            islands.append(island)

    bpy.ops.object.mode_set(mode="OBJECT")  # Back to object mode
    return islands


def calculate_uv_area(uv_x: int, uv_y: int, obj, islands):
    """Calculate UV island areas relative to 0-1 UV space and convert to pixels."""
    uv_layer = obj.data.uv_layers.active.data
    uv_areas = []

    uvmap_size = uv_x * uv_y

    batch_print = set()

    for island_num, island in enumerate(islands):
        total_area = 0
        for face_idx in island:
            poly = obj.data.polygons[face_idx]
            uvs = [uv_layer[loop_idx].uv for loop_idx in poly.loop_indices]

            # Shoelace formula for polygon area
            area = 0.5 * abs(sum((uvs[i][0] * uvs[i - 1][1] - uvs[i - 1][0] * uvs[i][1]) for i in range(len(uvs))))
            total_area += area

        # Convert relative UV area to pixel area
        island_pixel_area = total_area * uvmap_size
        # Derive pixel area peercentage directly since total area is 0-1
        pixel_area_pct = total_area * 100

        batch_print.add(
            f"{obj.name} | Island {island_num}: Relative UV Area: {total_area} | Pixel Area: {island_pixel_area:.2f} px² | Pixel Area Percentage: {pixel_area_pct}%"
        )

        uv_areas.append(
            (total_area, island_pixel_area, pixel_area_pct)
        )  # Store UV area and pixel area coverage and pixel area percentage

    if batch_print:
        log.debug(f"\n".join(batch_print))

    return uv_areas


def select_small_uv_islands(
    obj,
    uv_x: int,
    uv_y: int,
    threshold=THRESHOLD,
    threshold_px_coverage=THRESHOLD_PX_COVERAGE,
    threshold_pct=THRESHOLD_PCT,
) -> tuple[list, set, set]:
    """
    Selects UV islands that are below a given threshold and returns the respective UV Islands, their faces and vertices.

    :returns: Tuple of 3 `list`: Small Islands, Selected Faces, Selected Vertices
    :rtype: Union[list, list, list]
    """

    log.debug(f"Selecting Small UV Islands")
    log.debug(f"Obj: {obj}")
    log.debug(f"UV X: {uv_x}")
    log.debug(f"UV Y: {uv_y}")
    log.debug(f"Threshold: {threshold}")
    log.debug(f"Threshold Pixel Coverage: {threshold_px_coverage}")
    log.debug(f"Threshold Percent: {threshold_pct}")

    uv_island_sync = bpy.context.scene.tool_settings.use_uv_select_sync

    # Disable sync
    bpy.context.scene.tool_settings.use_uv_select_sync = False

    islands = get_uv_islands(obj)
    areas = calculate_uv_area(uv_x, uv_y, obj, islands)

    small_islands = []
    selected_faces = set()
    selected_verts = set()

    batch_print = set()

    for i, (relative_area, island_pixel_area, pixel_area_pct) in enumerate(areas):
        if relative_area <= threshold:
            small_islands.append(islands[i])
            selected_faces.update(islands[i])
            batch_print.add(f"{obj.name} | Island {i} too small: Relative UV Area: {relative_area}")
        elif island_pixel_area <= threshold_px_coverage:
            small_islands.append(islands[i])
            selected_faces.update(islands[i])
            batch_print.add(f"{obj.name} | Island {i} too small: Pixel Area: {island_pixel_area:.2f} px²")
        elif pixel_area_pct <= threshold_pct:
            small_islands.append(islands[i])
            selected_faces.update(islands[i])
            batch_print.add(f"{obj.name} | Island {i} too small: Pixel Area Percentage: {pixel_area_pct}%")

    log.debug(f"\n".join(batch_print))

    # Switch to Edit Mode to select faces
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")

    mesh = bmesh.from_edit_mesh(obj.data)

    for face in mesh.faces:
        if face.index in selected_faces:
            face.select = True
            selected_verts.update([vert.index for vert in face.verts])  # Store vertex indices

    bmesh.update_edit_mesh(obj.data, loop_triangles=True)  # Update the mesh
    bpy.ops.object.mode_set(mode="OBJECT")  # Switch back to Object Mode

    # Restore (or not) UV Island Sync
    bpy.context.scene.tool_settings.use_uv_select_sync = uv_island_sync

    return small_islands, selected_faces, selected_verts


if __name__ == "__main__":
    # Iterate through selected objects
    for obj in bpy.context.selected_objects:
        if obj.type == "MESH":
            small_islands, small_faces, small_verts = select_small_uv_islands(
                obj, TEXTURE_SIZE_X, TEXTURE_SIZE_Y, threshold=THRESHOLD
            )
            log.info(
                f"Object: {obj.name}, Small UV Islands Selected: {len(small_faces)} Faces, {len(small_verts)} Vertices"
            )
