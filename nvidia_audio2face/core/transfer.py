"""Transfer shape keys between meshes using surface proximity.

Projects blendshape deformations from a source mesh (e.g., the demo head)
onto a target mesh using BVH tree nearest-point lookup and barycentric
interpolation. This allows users to transfer ARKit blendshapes from the
bundled demo head to their own custom face models.
"""
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .. import constants


def transfer_shape_keys(source_obj, target_obj, shape_key_names=None):
    """Transfer shape key deformations from source mesh to target mesh.

    For each vertex on the target mesh, finds the nearest point on the
    source mesh's surface, then interpolates the shape key delta using
    barycentric coordinates of the enclosing triangle.

    Args:
        source_obj: Blender mesh object with shape keys (e.g., demo head).
        target_obj: Blender mesh object to receive transferred shape keys.
        shape_key_names: Optional list of shape key names to transfer.
                         Defaults to all 52 ARKit blendshape names.

    Returns:
        Number of shape keys successfully transferred.

    Raises:
        ValueError: If source mesh has no shape keys.
    """
    if shape_key_names is None:
        shape_key_names = constants.ARKIT_BLENDSHAPE_NAMES

    if not source_obj.data.shape_keys:
        raise ValueError("Source mesh has no shape keys to transfer")

    source_keys = source_obj.data.shape_keys.key_blocks
    if "Basis" not in source_keys:
        raise ValueError("Source mesh has no Basis shape key")

    source_basis = source_keys["Basis"]

    # Build polygon list from source mesh
    source_mesh = source_obj.data
    source_verts = [source_basis.data[i].co.copy() for i in range(len(source_mesh.vertices))]
    source_polys = [tuple(p.vertices) for p in source_mesh.polygons]

    # Build BVH tree from source mesh basis positions
    bvh = BVHTree.FromPolygons(source_verts, source_polys)

    # Ensure target has Basis shape key
    if not target_obj.data.shape_keys:
        target_obj.shape_key_add(name="Basis")

    target_mesh = target_obj.data
    target_basis = target_obj.data.shape_keys.key_blocks["Basis"]

    transferred = 0

    for sk_name in shape_key_names:
        if sk_name not in source_keys:
            continue

        source_sk = source_keys[sk_name]

        # Pre-compute source deltas for this shape key
        source_deltas = []
        for i in range(len(source_mesh.vertices)):
            delta = source_sk.data[i].co - source_basis.data[i].co
            source_deltas.append(delta)

        # Check if this shape key has any actual deformation
        has_deformation = any(d.length > 1e-8 for d in source_deltas)
        if not has_deformation:
            # Still create the shape key (empty), but skip the expensive transfer
            if sk_name not in target_obj.data.shape_keys.key_blocks:
                target_obj.shape_key_add(name=sk_name)
            transferred += 1
            continue

        # Create or get target shape key
        if sk_name in target_obj.data.shape_keys.key_blocks:
            target_sk = target_obj.data.shape_keys.key_blocks[sk_name]
        else:
            target_sk = target_obj.shape_key_add(name=sk_name)

        # Transfer deformations to each target vertex
        for vi in range(len(target_mesh.vertices)):
            target_co = target_basis.data[vi].co

            # Find nearest point on source mesh surface
            location, normal, face_index, distance = bvh.find_nearest(target_co)

            if location is None or face_index is None:
                continue

            # Get face vertex indices
            face_vert_indices = source_polys[face_index]

            if len(face_vert_indices) < 3:
                continue

            # Use first 3 vertices of the face for barycentric interpolation
            v0 = source_verts[face_vert_indices[0]]
            v1 = source_verts[face_vert_indices[1]]
            v2 = source_verts[face_vert_indices[2]]

            bary = _barycentric_coords(location, v0, v1, v2)

            # Interpolate delta from the three triangle vertices
            d0 = source_deltas[face_vert_indices[0]]
            d1 = source_deltas[face_vert_indices[1]]
            d2 = source_deltas[face_vert_indices[2]]

            delta = d0 * bary[0] + d1 * bary[1] + d2 * bary[2]

            # Apply interpolated delta to target vertex
            if delta.length > 1e-10:
                target_sk.data[vi].co = target_co + delta

        transferred += 1

    return transferred


def _barycentric_coords(point, v0, v1, v2):
    """Compute barycentric coordinates of a point in a triangle.

    Returns (w0, w1, w2) such that point ~= w0*v0 + w1*v1 + w2*v2.
    Coordinates are clamped and normalized to handle edge cases.
    """
    edge1 = v1 - v0
    edge2 = v2 - v0
    v_p = point - v0

    dot11 = edge1.dot(edge1)
    dot12 = edge1.dot(edge2)
    dot1p = edge1.dot(v_p)
    dot22 = edge2.dot(edge2)
    dot2p = edge2.dot(v_p)

    denom = dot11 * dot22 - dot12 * dot12

    if abs(denom) < 1e-12:
        # Degenerate triangle — equal weights
        return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)

    inv = 1.0 / denom
    u = (dot22 * dot1p - dot12 * dot2p) * inv  # weight for v1
    v = (dot11 * dot2p - dot12 * dot1p) * inv  # weight for v2
    w = 1.0 - u - v                             # weight for v0

    # Clamp to valid range (handles numerical imprecision near edges)
    w = max(0.0, min(1.0, w))
    u = max(0.0, min(1.0, u))
    v = max(0.0, min(1.0, v))

    # Renormalize
    total = w + u + v
    if total > 0.0:
        return (w / total, u / total, v / total)

    return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
