"""Generate a demo head mesh with ARKit blendshape deformations.

Creates a procedural head mesh with all 52 ARKit blendshapes that have
actual vertex deformations. This lets users test the addon immediately
without needing an external model.

The head is a modified UV sphere (~24cm diameter) with face-like proportions.
Each blendshape uses region-based vertex displacement with smooth falloff.
"""
import bpy
import bmesh
import math
from mathutils import Vector

from .. import constants


# ---------------------------------------------------------------------------
# Blendshape deformation definitions
# ---------------------------------------------------------------------------
# Format per entry: list of (center_x, center_y, center_z, radius, disp_x, disp_y, disp_z)
#
# Coordinate system:
#   Head centered at origin, facing -Y, Z up.
#   UV sphere radius = 0.12m, scaled: X * 0.85, Z * 1.15 (oval head shape).
#   After scaling, approximate extents:
#     X: -0.10 to 0.10     (width)
#     Y: -0.12 to 0.12     (depth)
#     Z: -0.14 to 0.14     (height)
#
#   The front of the face is at Y ~ -0.10 to -0.12.
#   Eyes sit at Z ~ 0.03, mouth at Z ~ -0.04, brows at Z ~ 0.065.

_DEFS = {
    # === Eyes (blink = upper lid drops toward lower lid) ===
    "EyeBlinkLeft":     [( 0.035, -0.095, 0.040, 0.020, 0.000, 0.000, -0.008)],
    "EyeBlinkRight":    [(-0.035, -0.095, 0.040, 0.020, 0.000, 0.000, -0.008)],
    "EyeLookDownLeft":  [( 0.035, -0.100, 0.030, 0.018, 0.000, 0.000, -0.004)],
    "EyeLookDownRight": [(-0.035, -0.100, 0.030, 0.018, 0.000, 0.000, -0.004)],
    "EyeLookInLeft":    [( 0.035, -0.100, 0.035, 0.015, -0.003, 0.000, 0.000)],
    "EyeLookInRight":   [(-0.035, -0.100, 0.035, 0.015,  0.003, 0.000, 0.000)],
    "EyeLookOutLeft":   [( 0.035, -0.100, 0.035, 0.015,  0.003, 0.000, 0.000)],
    "EyeLookOutRight":  [(-0.035, -0.100, 0.035, 0.015, -0.003, 0.000, 0.000)],
    "EyeLookUpLeft":    [( 0.035, -0.100, 0.040, 0.018, 0.000, 0.000,  0.004)],
    "EyeLookUpRight":   [(-0.035, -0.100, 0.040, 0.018, 0.000, 0.000,  0.004)],
    "EyeSquintLeft":    [( 0.035, -0.092, 0.028, 0.022, 0.000, 0.000,  0.004)],
    "EyeSquintRight":   [(-0.035, -0.092, 0.028, 0.022, 0.000, 0.000,  0.004)],
    "EyeWideLeft":      [( 0.035, -0.092, 0.045, 0.022, 0.000, 0.000,  0.006)],
    "EyeWideRight":     [(-0.035, -0.092, 0.045, 0.022, 0.000, 0.000,  0.006)],

    # === Jaw ===
    "JawForward":  [(0.000, -0.090, -0.080, 0.060, 0.000, -0.012, 0.000)],
    "JawLeft":     [(0.000, -0.090, -0.080, 0.060, 0.008, 0.000, 0.000)],
    "JawRight":    [(0.000, -0.090, -0.080, 0.060, -0.008, 0.000, 0.000)],
    "JawOpen":     [(0.000, -0.090, -0.090, 0.060, 0.000, 0.000, -0.025)],

    # === Mouth ===
    "MouthClose":        [(0.000, -0.108, -0.040, 0.025, 0.000, 0.000,  0.004)],
    "MouthFunnel":       [(0.000, -0.115, -0.035, 0.022, 0.000, -0.008, 0.000)],
    "MouthPucker":       [(0.000, -0.115, -0.035, 0.018, 0.000, -0.010, 0.000)],
    "MouthLeft":         [(0.000, -0.108, -0.035, 0.035, 0.010, 0.000, 0.000)],
    "MouthRight":        [(0.000, -0.108, -0.035, 0.035, -0.010, 0.000, 0.000)],
    "MouthSmileLeft":    [( 0.035, -0.100, -0.035, 0.022,  0.006, 0.000, 0.008)],
    "MouthSmileRight":   [(-0.035, -0.100, -0.035, 0.022, -0.006, 0.000, 0.008)],
    "MouthFrownLeft":    [( 0.035, -0.100, -0.040, 0.022,  0.002, 0.000, -0.008)],
    "MouthFrownRight":   [(-0.035, -0.100, -0.040, 0.022, -0.002, 0.000, -0.008)],
    "MouthDimpleLeft":   [( 0.040, -0.095, -0.035, 0.018,  0.004, -0.004, 0.000)],
    "MouthDimpleRight":  [(-0.040, -0.095, -0.035, 0.018, -0.004, -0.004, 0.000)],
    "MouthStretchLeft":  [( 0.040, -0.100, -0.035, 0.020,  0.008, 0.000, 0.000)],
    "MouthStretchRight": [(-0.040, -0.100, -0.035, 0.020, -0.008, 0.000, 0.000)],
    "MouthRollLower":    [(0.000, -0.110, -0.048, 0.025, 0.000,  0.006,  0.002)],
    "MouthRollUpper":    [(0.000, -0.110, -0.025, 0.025, 0.000,  0.006, -0.002)],
    "MouthShrugLower":   [(0.000, -0.112, -0.048, 0.020, 0.000, -0.004,  0.003)],
    "MouthShrugUpper":   [(0.000, -0.112, -0.025, 0.020, 0.000, -0.004, -0.002)],
    "MouthPressLeft":    [( 0.020, -0.110, -0.035, 0.018, 0.000,  0.004, 0.000)],
    "MouthPressRight":   [(-0.020, -0.110, -0.035, 0.018, 0.000,  0.004, 0.000)],
    "MouthLowerDownLeft":  [( 0.012, -0.108, -0.050, 0.018, 0.000, 0.000, -0.006)],
    "MouthLowerDownRight": [(-0.012, -0.108, -0.050, 0.018, 0.000, 0.000, -0.006)],
    "MouthUpperUpLeft":    [( 0.012, -0.110, -0.022, 0.018, 0.000, 0.000,  0.006)],
    "MouthUpperUpRight":   [(-0.012, -0.110, -0.022, 0.018, 0.000, 0.000,  0.006)],

    # === Brows ===
    "BrowDownLeft":     [( 0.030, -0.092, 0.060, 0.025, 0.000, 0.000, -0.008)],
    "BrowDownRight":    [(-0.030, -0.092, 0.060, 0.025, 0.000, 0.000, -0.008)],
    "BrowInnerUp":      [(0.000, -0.092, 0.068, 0.030, 0.000, 0.000,  0.010)],
    "BrowOuterUpLeft":  [( 0.050, -0.085, 0.060, 0.020, 0.000, 0.000,  0.008)],
    "BrowOuterUpRight": [(-0.050, -0.085, 0.060, 0.020, 0.000, 0.000,  0.008)],

    # === Cheeks ===
    "CheekPuff":        [( 0.060, -0.075, 0.000, 0.035,  0.008, -0.006, 0.000),
                          (-0.060, -0.075, 0.000, 0.035, -0.008, -0.006, 0.000)],
    "CheekSquintLeft":  [( 0.040, -0.090, 0.020, 0.022, 0.000, 0.000,  0.005)],
    "CheekSquintRight": [(-0.040, -0.090, 0.020, 0.022, 0.000, 0.000,  0.005)],

    # === Nose ===
    "NoseSneerLeft":    [( 0.015, -0.108, 0.005, 0.018,  0.002, 0.000,  0.004)],
    "NoseSneerRight":   [(-0.015, -0.108, 0.005, 0.018, -0.002, 0.000,  0.004)],
}


def create_demo_head(name="A2F_DemoHead"):
    """Create a demo head mesh with all 52 ARKit blendshape deformations.

    The head is a UV sphere shaped into an oval, with smooth vertex
    deformations for each blendshape.

    Args:
        name: Name for the Blender object.

    Returns:
        The created Blender object.
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    # Higher resolution sphere for smoother deformations
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=0.12)

    # Shape into head: narrower (X), taller (Z), chin taper
    for v in bm.verts:
        # Make oval: narrower X, taller Z
        v.co.x *= 0.85
        v.co.z *= 1.15

        # Taper chin (lower face gets narrower)
        if v.co.z < -0.02:
            taper = 1.0 - max(0.0, (-v.co.z - 0.02)) * 2.5
            taper = max(0.3, taper)
            v.co.x *= taper
            v.co.y *= taper * 0.95 + 0.05  # Slight depth taper too

        # Slight forward push for nose/mouth area (front face protrusion)
        if v.co.y < -0.06:
            front_factor = max(0.0, (-v.co.y - 0.06)) / 0.06
            if abs(v.co.x) < 0.04 and -0.02 < v.co.z < 0.02:
                v.co.y -= 0.008 * front_factor  # Nose bump

    bm.to_mesh(mesh)
    bm.free()

    # Create object and link to scene
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Add Basis shape key (must be first)
    basis_sk = obj.shape_key_add(name="Basis")
    basis_data = obj.data.shape_keys.key_blocks["Basis"].data

    # Create all 52 ARKit shape keys with deformations
    for sk_name in constants.ARKIT_BLENDSHAPE_NAMES:
        sk = obj.shape_key_add(name=sk_name)

        if sk_name not in _DEFS:
            continue

        for cx, cy, cz, radius, dx, dy, dz in _DEFS[sk_name]:
            center = Vector((cx, cy, cz))
            disp = Vector((dx, dy, dz))

            for i in range(len(sk.data)):
                basis_co = basis_data[i].co
                dist = (basis_co - center).length

                if dist < radius:
                    # Smooth quadratic falloff from center
                    t = 1.0 - (dist / radius)
                    weight = t * t * (3.0 - 2.0 * t)  # Smoothstep
                    sk.data[i].co = basis_co + disp * weight

    # Set display to solid for better visibility
    obj.display_type = 'SOLID'

    return obj
