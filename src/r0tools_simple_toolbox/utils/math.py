from mathutils import Matrix, Vector


def get_selection_orientation_matrix(obj, bm) -> Matrix:
    """
    Compute a world-space rotation matrix (4x4) representing the 'Normal' orientation of the current bmesh selection.
    Returns None if there is no valid selection.
    """
    bm.normal_update()

    mat3 = obj.matrix_world.to_3x3()
    normal_mat = mat3.inverted_safe().transposed()  # correct transform for normals

    selected_faces = [f for f in bm.faces if f.select]
    selected_edges = [e for e in bm.edges if e.select]
    selected_verts = [v for v in bm.verts if v.select]

    normal_local = None
    tangent_local = None

    if selected_faces:
        n = Vector()
        for f in selected_faces:
            n += f.normal * f.calc_area()
        if n.length == 0:
            n = selected_faces[0].normal.copy()
        normal_local = n.normalized()
        v0, v1 = selected_faces[0].verts[0], selected_faces[0].verts[1]
        tangent_local = v1.co - v0.co

    elif selected_edges:
        n = Vector()
        has_face_normal = False
        for e in selected_edges:
            for f in e.link_faces:
                n += f.normal
                has_face_normal = True
        if not has_face_normal:
            for e in selected_edges:
                n += e.verts[0].normal + e.verts[1].normal
        if n.length == 0:
            n = Vector((0.0, 0.0, 1.0))
        normal_local = n.normalized()

        t = Vector()
        for e in selected_edges:
            d = e.verts[1].co - e.verts[0].co
            if d.dot(t) < 0:
                d = -d
            t += d
        tangent_local = t

    elif selected_verts:
        n = Vector()
        for v in selected_verts:
            n += v.normal
        if n.length == 0:
            n = Vector((0.0, 0.0, 1.0))
        normal_local = n.normalized()

        tangent_local = None
        for v in selected_verts:
            for e in v.link_edges:
                tangent_local = e.other_vert(v).co - v.co
                break
            if tangent_local:
                break
        if tangent_local is None:
            tangent_local = Vector((1.0, 0.0, 0.0))
    else:
        return None

    normal_world = (normal_mat @ normal_local).normalized()
    tangent_world = mat3 @ tangent_local

    if tangent_world.length < 1e-8 or abs(tangent_world.normalized().dot(normal_world)) > 0.9999:
        fallback = Vector((1.0, 0.0, 0.0))
        if abs(fallback.dot(normal_world)) > 0.9999:
            fallback = Vector((0.0, 1.0, 0.0))
        tangent_world = fallback

    tangent_world = (tangent_world - tangent_world.project(normal_world)).normalized()
    binormal_world = normal_world.cross(tangent_world).normalized()
    tangent_world = binormal_world.cross(normal_world).normalized()

    rotation = Matrix((tangent_world, binormal_world, normal_world)).transposed().to_4x4()
    return rotation
