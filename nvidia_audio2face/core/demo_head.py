"""Load the ICT-FaceKit demo head with ARKit blendshape deformations.

Loads a high-quality face model (26,719 vertices) from a compact binary
asset file pre-built from the ICT-FaceKit model (MIT License, USC Institute
for Creative Technologies). The model includes 51 ARKit-compatible blendshapes
with real vertex deformations covering eyes, brows, jaw, mouth, cheeks, and nose.

If the binary asset is missing, falls back to a simple procedural head.

Binary asset format (.bin, zlib-compressed):
    Header: magic "A2FM", version, counts
    Neutral mesh: vertices, faces (mixed tri/quad), UVs
    Expressions: sparse deltas per ARKit blendshape name
"""
import os
import struct
import zlib

import bpy
import bmesh
from mathutils import Vector

from .. import constants

# Path to the pre-built binary asset
_ASSET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "ict_facekit.bin")


def _load_binary_asset(filepath):
    """Load and decompress the binary face model asset.

    Returns:
        Tuple of (vertices, faces, uv_coords, uv_faces, expressions)
        where expressions is a dict of {arkit_name: [(vertex_idx, dx, dy, dz), ...]}
    """
    with open(filepath, "rb") as f:
        compressed = f.read()

    data = zlib.decompress(compressed)
    offset = 0

    def read(fmt):
        nonlocal offset
        size = struct.calcsize(fmt)
        values = struct.unpack_from(fmt, data, offset)
        offset += size
        return values

    # Header
    magic = data[offset:offset + 4]
    offset += 4
    if magic != b"A2FM":
        raise ValueError(f"Invalid asset file (bad magic: {magic!r})")

    version, num_verts, num_faces, num_uvs, num_expressions = read("<5I")
    if version != 1:
        raise ValueError(f"Unsupported asset version: {version}")

    # Neutral vertices
    vertices = []
    for _ in range(num_verts):
        x, y, z = read("<3f")
        vertices.append((x, y, z))

    # Faces (variable polygon size)
    faces = []
    for _ in range(num_faces):
        (n,) = read("<B")
        face = []
        for _ in range(n):
            (idx,) = read("<I")
            face.append(idx)
        faces.append(tuple(face))

    # UV coordinates
    uv_coords = []
    for _ in range(num_uvs):
        u, v = read("<2f")
        uv_coords.append((u, v))

    # UV faces
    uv_faces = []
    for _ in range(num_faces):
        (n,) = read("<B")
        uv_face = []
        for _ in range(n):
            (idx,) = read("<I")
            uv_face.append(idx)
        uv_faces.append(tuple(uv_face))

    # Expressions
    expressions = {}
    for _ in range(num_expressions):
        (name_len,) = read("<H")
        name = data[offset:offset + name_len].decode("utf-8")
        offset += name_len
        (num_deltas,) = read("<I")
        deltas = []
        for _ in range(num_deltas):
            vi, dx, dy, dz = read("<I3f")
            deltas.append((vi, dx, dy, dz))
        expressions[name] = deltas

    return vertices, faces, uv_coords, uv_faces, expressions


def _create_mesh_from_asset(name, vertices, faces, uv_coords, uv_faces):
    """Create a Blender mesh from parsed asset data."""
    mesh = bpy.data.meshes.new(name)

    # Create vertices and faces
    mesh.from_pydata(vertices, [], faces)

    # Create UV layer
    if uv_coords and uv_faces:
        uv_layer = mesh.uv_layers.new(name="UVMap")
        for fi, face in enumerate(mesh.polygons):
            if fi < len(uv_faces):
                for li, loop_idx in enumerate(face.loop_indices):
                    if li < len(uv_faces[fi]):
                        uv_idx = uv_faces[fi][li]
                        if uv_idx < len(uv_coords):
                            uv_layer.data[loop_idx].uv = uv_coords[uv_idx]

    mesh.update()
    mesh.validate()
    return mesh


def create_demo_head(name="ICT_FaceKit_Head"):
    """Create a demo head mesh with ARKit blendshape deformations.

    Loads the ICT-FaceKit model from the pre-built binary asset.
    Falls back to a simple procedural head if the asset is missing.

    Args:
        name: Name for the Blender object.

    Returns:
        The created Blender object.
    """
    if os.path.exists(_ASSET_PATH):
        return _create_from_asset(name)
    else:
        return _create_procedural_fallback(name)


def _create_from_asset(name):
    """Create head from ICT-FaceKit binary asset."""
    vertices, faces, uv_coords, uv_faces, expressions = _load_binary_asset(_ASSET_PATH)

    mesh = _create_mesh_from_asset(name, vertices, faces, uv_coords, uv_faces)

    # Create object and link to scene
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Add Basis shape key
    obj.shape_key_add(name="Basis")
    basis_data = obj.data.shape_keys.key_blocks["Basis"].data

    # Create ARKit shape keys with deformations from asset
    for sk_name in constants.ARKIT_BLENDSHAPE_NAMES:
        sk = obj.shape_key_add(name=sk_name)

        if sk_name not in expressions:
            continue

        for vi, dx, dy, dz in expressions[sk_name]:
            if vi < len(sk.data):
                basis_co = basis_data[vi].co
                sk.data[vi].co = (basis_co.x + dx, basis_co.y + dy, basis_co.z + dz)

    # Smooth shading for better appearance
    for poly in mesh.polygons:
        poly.use_smooth = True

    obj.display_type = 'SOLID'
    return obj


def _create_procedural_fallback(name):
    """Fallback: create a simple procedural head if binary asset is missing."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=0.12)

    # Shape into head
    for v in bm.verts:
        v.co.x *= 0.85
        v.co.z *= 1.15
        if v.co.z < -0.02:
            taper = max(0.3, 1.0 - max(0.0, (-v.co.z - 0.02)) * 2.5)
            v.co.x *= taper
            v.co.y *= taper * 0.95 + 0.05

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Add empty ARKit shape keys (no deformations in fallback)
    obj.shape_key_add(name="Basis")
    for sk_name in constants.ARKIT_BLENDSHAPE_NAMES:
        obj.shape_key_add(name=sk_name)

    obj.display_type = 'SOLID'
    return obj
