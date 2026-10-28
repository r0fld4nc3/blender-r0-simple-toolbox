import logging
from statistics import median

import bmesh

THRESHOLD = 0.00001  # Minimum area for an island to be considered "too small"
THRESHOLD_PX_COVERAGE = 80.0  # The "pixel area squared", or coverage in this case, is essentially the area of the UV island expressed in pixel units rather than in UV space (which ranges from 0 to 1)
THRESHOLD_PCT = 0.000475  # Minimum pixel percentage coverage for an island to be considered "too small"
TEXTURE_SIZE_X = 4096  # Texture resolution in pixels (e.g., 4096x4096)
TEXTURE_SIZE_Y = 4096  # Texture resolution in pixels (e.g., 4096x4096)
TEXTURE_SIZE_SQ = TEXTURE_SIZE_X * TEXTURE_SIZE_Y

log = logging.getLogger(__name__)


def get_uv_islands(bm, uv_layer):
    """Iterative. Faces are linked through shared UV vertices."""
    islands, visited = [], set()
    for seed in bm.faces:
        if seed in visited:
            continue
        visited.add(seed)
        island, stack = [seed], [seed]
        while stack:
            face = stack.pop()
            for loop in face.loops:
                uv = loop[uv_layer].uv
                for other in loop.vert.link_loops:
                    f = other.face
                    if f not in visited and other[uv_layer].uv == uv:
                        visited.add(f)
                        island.append(f)
                        stack.append(f)
        islands.append(island)
    return islands


def uv_face_area(face, uv_layer):
    uvs = [l[uv_layer].uv for l in face.loops]
    return 0.5 * abs(sum(uvs[i].x * uvs[i - 1].y - uvs[i - 1].x * uvs[i].y for i in range(len(uvs))))


def effective_thresholds(uv_x, uv_y, threshold=None, threshold_px_coverage=None, threshold_pct=None):
    """
    Convert every enabled threshold to relative UV area (0-1) so the ycan be compared directly.

    Returns:
        `dict` of {check name: relative area cutoff}. Empty if not check is enabled.
    """

    px_scale = uv_x * uv_y
    cutoffs = {}

    if threshold is not None:
        cutoffs["relative"] = threshold

    if threshold_px_coverage is not None:
        cutoffs["pixels"] = threshold_px_coverage / px_scale

    if threshold_pct is not None:
        cutoffs["percentage"] = threshold_pct / 100

    return cutoffs


def select_small_uv_islands(obj, uv_x, uv_y, threshold=None, threshold_px_coverage=None, threshold_pct=None):
    """Must be called in Object Mode. A threshold of None means that check is disabled."""
    me = obj.data
    if not me.uv_layers:
        log.warning(f"[{obj.name}] Has no UV maps, skipped")
        return [], set(), set()

    bm = bmesh.new()
    bm.from_mesh(me)
    uv_layer = bm.loops.layers.uv.active
    log.info(f"[{obj.name}] Using UV map '{uv_layer.name}' | {len(bm.faces)} face(s), {len(bm.verts)} vert(s)")

    # Clear previous mesh and UV selection
    for seq in (bm.verts, bm.edges, bm.faces):
        for elem in seq:
            elem.select = False
    for f in bm.faces:
        _set_face_uv_select(f, uv_layer, False)

    islands = get_uv_islands(bm, uv_layer)
    log.debug(f"[{obj.name}] Found {len(islands)} UV island(s).")

    px_scale = uv_x * uv_y
    small_islands, sel_faces, sel_verts = [], set(), set()
    areas = []
    reason_counts = {"relative": 0, "pixels": 0, "percentage": 0}
    log_islands = log.isEnabledFor(logging.DEBUG)

    for i, island in enumerate(islands):
        area = sum(uv_face_area(f, uv_layer) for f in island)
        px_area = area * px_scale
        pct_area = area * 100
        areas.append(area)

        reasons = []
        if threshold is not None and area <= threshold:
            reasons.append("relative")
        if threshold_px_coverage is not None and px_area <= threshold_px_coverage:
            reasons.append("pixels")
        if threshold_pct is not None and pct_area <= threshold_pct:
            reasons.append("percentage")

        if log_islands:
            status = f"SMALL [{', '.join(reasons)}]" if reasons else "ok"
            log.debug(
                f"[{obj.name}] Island {i:>4} | {len(island):>5} face(s) | "
                f"rel {area:.3e} | {px_area:>12.2f} px² | {pct_area:.6f}% | {status}"
            )

        if not reasons:
            continue

        for r in reasons:
            reason_counts[r] += 1

        small_islands.append([f.index for f in island])
        for f in island:
            f.select = True  # also selects edges/verts
            _set_face_uv_select(f, uv_layer, True)
            sel_faces.add(f.index)
            sel_verts.update(v.index for v in f.verts)

    bm.to_mesh(me)
    bm.free()
    me.update()

    _log_object_summary(obj.name, areas, len(small_islands), len(sel_faces), len(sel_verts), reason_counts, px_scale)
    return small_islands, sel_faces, sel_verts


def _log_object_summary(name, areas, n_small, n_faces, n_verts, reason_counts, px_scale):
    if not areas:
        log.info(f"[{name}] Mesh has no faces, nothing to check")
        return

    log.info(f"[{name}] {len(areas)} island(s), {n_small} small " f"({n_faces} face(s), {n_verts} vert(s) selected)")
    log.info(
        f"[{name}] Island area min / median / max: "
        f"{min(areas) * px_scale:.2f} / {median(areas) * px_scale:.2f} / {max(areas) * px_scale:.2f} px²"
    )
    # Stacked/overlapping islands are each counted, so this can exceed 100%
    log.info(f"[{name}] UV space used: {sum(areas) * 100:.2f}%")

    if n_small:
        # One island can trip several checks, so these can add up to more than n_small
        triggered = ", ".join(f"{k}: {v}" for k, v in reason_counts.items() if v)
        log.info(f"[{name}] Triggered by: {triggered}")

    zero_area = sum(1 for a in areas if a == 0.0)
    if zero_area:
        log.warning(f"[{name}] {zero_area} island(s) have zero UV area (degenerate faces or collapsed UVs)")


def _set_face_uv_select(face, uv_layer, state: bool):
    if hasattr(face, "uv_select"):  # Blender 5.0+
        face.uv_select = state
        for loop in face.loops:
            loop.uv_select_vert = state
            loop.uv_select_edge = state
    else:  # Blender 3.2 - 4.x
        for loop in face.loops:
            luv = loop[uv_layer]
            luv.select = state
            luv.select_edge = state
