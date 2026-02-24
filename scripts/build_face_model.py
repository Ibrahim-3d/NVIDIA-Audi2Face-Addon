#!/usr/bin/env python
"""Build compact binary face model asset from ICT-FaceKit OBJ files.

Reads the ICT-FaceKit expression OBJs, computes sparse deltas from the
neutral mesh, maps names to ARKit standard, and produces a single
compressed binary file suitable for shipping with the addon.

Usage:
    python scripts/build_face_model.py <path-to-FaceXModel-dir> <output-path>

Example:
    python scripts/build_face_model.py /tmp/ICT-FaceKit/FaceXModel nvidia_audio2face/assets/ict_facekit.bin
"""
import json
import os
import struct
import sys
import zlib

# Threshold for considering a vertex delta as non-zero
DELTA_THRESHOLD = 1e-7

# ICT-FaceKit expression name -> ARKit standard name mapping
# ICT splits BrowInnerUp and CheekPuff into L/R; ARKit has them as single shapes.
ICT_TO_ARKIT = {
    "browDown_L": "BrowDownLeft",
    "browDown_R": "BrowDownRight",
    "browInnerUp_L": "BrowInnerUp",    # Combined L+R
    "browInnerUp_R": "BrowInnerUp",    # Combined L+R
    "browOuterUp_L": "BrowOuterUpLeft",
    "browOuterUp_R": "BrowOuterUpRight",
    "cheekPuff_L": "CheekPuff",        # Combined L+R
    "cheekPuff_R": "CheekPuff",        # Combined L+R
    "cheekSquint_L": "CheekSquintLeft",
    "cheekSquint_R": "CheekSquintRight",
    "eyeBlink_L": "EyeBlinkLeft",
    "eyeBlink_R": "EyeBlinkRight",
    "eyeLookDown_L": "EyeLookDownLeft",
    "eyeLookDown_R": "EyeLookDownRight",
    "eyeLookIn_L": "EyeLookInLeft",
    "eyeLookIn_R": "EyeLookInRight",
    "eyeLookOut_L": "EyeLookOutLeft",
    "eyeLookOut_R": "EyeLookOutRight",
    "eyeLookUp_L": "EyeLookUpLeft",
    "eyeLookUp_R": "EyeLookUpRight",
    "eyeSquint_L": "EyeSquintLeft",
    "eyeSquint_R": "EyeSquintRight",
    "eyeWide_L": "EyeWideLeft",
    "eyeWide_R": "EyeWideRight",
    "jawForward": "JawForward",
    "jawLeft": "JawLeft",
    "jawOpen": "JawOpen",
    "jawRight": "JawRight",
    "mouthClose": "MouthClose",
    "mouthDimple_L": "MouthDimpleLeft",
    "mouthDimple_R": "MouthDimpleRight",
    "mouthFrown_L": "MouthFrownLeft",
    "mouthFrown_R": "MouthFrownRight",
    "mouthFunnel": "MouthFunnel",
    "mouthLeft": "MouthLeft",
    "mouthLowerDown_L": "MouthLowerDownLeft",
    "mouthLowerDown_R": "MouthLowerDownRight",
    "mouthPress_L": "MouthPressLeft",
    "mouthPress_R": "MouthPressRight",
    "mouthPucker": "MouthPucker",
    "mouthRight": "MouthRight",
    "mouthRollLower": "MouthRollLower",
    "mouthRollUpper": "MouthRollUpper",
    "mouthShrugLower": "MouthShrugLower",
    "mouthShrugUpper": "MouthShrugUpper",
    "mouthSmile_L": "MouthSmileLeft",
    "mouthSmile_R": "MouthSmileRight",
    "mouthStretch_L": "MouthStretchLeft",
    "mouthStretch_R": "MouthStretchRight",
    "mouthUpperUp_L": "MouthUpperUpLeft",
    "mouthUpperUp_R": "MouthUpperUpRight",
    "noseSneer_L": "NoseSneerLeft",
    "noseSneer_R": "NoseSneerRight",
}


def parse_obj(filepath):
    """Parse OBJ file, return (vertices, faces, uv_coords, uv_faces).

    vertices: list of (x, y, z) float tuples
    faces: list of tuples of vertex indices (0-based)
    uv_coords: list of (u, v) float tuples
    uv_faces: list of tuples of UV indices (0-based)
    """
    vertices = []
    faces = []
    uv_coords = []
    uv_faces = []

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith("v "):
                parts = line.split()
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith("vt "):
                parts = line.split()
                uv_coords.append((float(parts[1]), float(parts[2])))
            elif line.startswith("f "):
                parts = line.split()[1:]
                face_v = []
                face_uv = []
                for p in parts:
                    indices = p.split("/")
                    face_v.append(int(indices[0]) - 1)  # OBJ is 1-based
                    if len(indices) > 1 and indices[1]:
                        face_uv.append(int(indices[1]) - 1)
                faces.append(tuple(face_v))
                if face_uv:
                    uv_faces.append(tuple(face_uv))

    return vertices, faces, uv_coords, uv_faces


def parse_obj_vertices_only(filepath):
    """Parse only vertex positions from an OBJ file (faster)."""
    vertices = []
    with open(filepath) as f:
        for line in f:
            if line.startswith("v "):
                parts = line.split()
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
    return vertices


def compute_sparse_deltas(neutral_verts, expression_verts):
    """Compute sparse delta between expression and neutral vertices.

    Returns list of (vertex_index, dx, dy, dz) for non-zero deltas.
    """
    deltas = []
    for i, (nv, ev) in enumerate(zip(neutral_verts, expression_verts)):
        dx = ev[0] - nv[0]
        dy = ev[1] - nv[1]
        dz = ev[2] - nv[2]
        if abs(dx) > DELTA_THRESHOLD or abs(dy) > DELTA_THRESHOLD or abs(dz) > DELTA_THRESHOLD:
            deltas.append((i, dx, dy, dz))
    return deltas


def build_binary(neutral_verts, faces, uv_coords, uv_faces, expressions):
    """Build binary data blob.

    Format:
        HEADER:
            4 bytes: magic "A2FM"
            uint32: version (1)
            uint32: num_vertices
            uint32: num_faces
            uint32: num_uv_coords
            uint32: num_expressions

        NEUTRAL VERTICES:
            float32[num_vertices * 3]: x,y,z interleaved

        FACES (variable-size polygons):
            For each face:
                uint8: num_verts_in_face
                uint32[num_verts_in_face]: vertex indices

        UV COORDS:
            float32[num_uv_coords * 2]: u,v interleaved

        UV FACES:
            For each face:
                uint8: num_verts_in_face
                uint32[num_verts_in_face]: UV indices

        EXPRESSIONS (repeated):
            uint16: name_length
            bytes[name_length]: name (UTF-8)
            uint32: num_deltas
            For each delta:
                uint32: vertex_index
                float32: dx, dy, dz
    """
    data = bytearray()

    num_verts = len(neutral_verts)
    num_faces = len(faces)
    num_uvs = len(uv_coords)
    num_expressions = len(expressions)

    # Header
    data.extend(b"A2FM")
    data.extend(struct.pack("<5I", 1, num_verts, num_faces, num_uvs, num_expressions))

    # Neutral vertices
    for x, y, z in neutral_verts:
        data.extend(struct.pack("<3f", x, y, z))

    # Faces (variable polygon size)
    for face in faces:
        data.extend(struct.pack("<B", len(face)))
        for idx in face:
            data.extend(struct.pack("<I", idx))

    # UV coordinates
    for u, v in uv_coords:
        data.extend(struct.pack("<2f", u, v))

    # UV faces
    for uv_face in uv_faces:
        data.extend(struct.pack("<B", len(uv_face)))
        for idx in uv_face:
            data.extend(struct.pack("<I", idx))

    # Expressions
    for arkit_name, deltas in expressions.items():
        name_bytes = arkit_name.encode("utf-8")
        data.extend(struct.pack("<H", len(name_bytes)))
        data.extend(name_bytes)
        data.extend(struct.pack("<I", len(deltas)))
        for vi, dx, dy, dz in deltas:
            data.extend(struct.pack("<I3f", vi, dx, dy, dz))

    return bytes(data)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <FaceXModel-dir> <output-path>")
        sys.exit(1)

    model_dir = sys.argv[1]
    output_path = sys.argv[2]

    # Load config to get expression list
    config_path = os.path.join(model_dir, "vertex_indices.json")
    with open(config_path) as f:
        config = json.load(f)

    ict_expressions = config["expressions"]
    print(f"Found {len(ict_expressions)} ICT expressions")

    # Parse neutral mesh
    neutral_path = os.path.join(model_dir, "generic_neutral_mesh.obj")
    print(f"Parsing neutral mesh: {neutral_path}")
    neutral_verts, faces, uv_coords, uv_faces = parse_obj(neutral_path)
    print(f"  Vertices: {len(neutral_verts)}, Faces: {len(faces)}, UVs: {len(uv_coords)}")

    # Parse each expression and compute deltas
    # Group by ARKit name (to handle combined shapes like BrowInnerUp, CheekPuff)
    arkit_deltas = {}

    for ict_name in ict_expressions:
        arkit_name = ICT_TO_ARKIT.get(ict_name)
        if arkit_name is None:
            print(f"  Skipping unmapped expression: {ict_name}")
            continue

        obj_path = os.path.join(model_dir, f"{ict_name}.obj")
        if not os.path.exists(obj_path):
            print(f"  Warning: OBJ not found: {obj_path}")
            continue

        print(f"  Parsing {ict_name} -> {arkit_name}")
        expr_verts = parse_obj_vertices_only(obj_path)

        if len(expr_verts) != len(neutral_verts):
            print(f"    ERROR: vertex count mismatch ({len(expr_verts)} vs {len(neutral_verts)})")
            continue

        deltas = compute_sparse_deltas(neutral_verts, expr_verts)

        if arkit_name in arkit_deltas:
            # Combine with existing (for BrowInnerUp, CheekPuff)
            existing = {d[0]: (d[1], d[2], d[3]) for d in arkit_deltas[arkit_name]}
            for vi, dx, dy, dz in deltas:
                if vi in existing:
                    ox, oy, oz = existing[vi]
                    existing[vi] = (ox + dx, oy + dy, oz + dz)
                else:
                    existing[vi] = (dx, dy, dz)
            arkit_deltas[arkit_name] = [
                (vi, d[0], d[1], d[2]) for vi, d in sorted(existing.items())
            ]
            print(f"    Combined -> {len(arkit_deltas[arkit_name])} deltas")
        else:
            arkit_deltas[arkit_name] = deltas
            print(f"    {len(deltas)} non-zero deltas")

    print(f"\nTotal ARKit expressions: {len(arkit_deltas)}")
    for name, deltas in sorted(arkit_deltas.items()):
        print(f"  {name}: {len(deltas)} deltas")

    # Build binary
    print("\nBuilding binary data...")
    raw_data = build_binary(neutral_verts, faces, uv_coords, uv_faces, arkit_deltas)
    print(f"  Raw size: {len(raw_data):,} bytes ({len(raw_data) / 1024 / 1024:.1f} MB)")

    # Compress
    compressed = zlib.compress(raw_data, level=9)
    print(f"  Compressed size: {len(compressed):,} bytes ({len(compressed) / 1024 / 1024:.1f} MB)")

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(compressed)

    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
