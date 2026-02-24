"""Apply animation data to Blender mesh shape keys."""
from .. import constants
from .client import AnimationFrame


def apply_animation(
    mesh_obj,
    frames: list[AnimationFrame],
    mapping: dict[str, str],
    scene_fps: float,
    frame_offset: int = 1,
    multipliers: dict[str, float] | None = None,
) -> int:
    """Apply animation frames to mesh shape keys as keyframes.

    Args:
        mesh_obj: Blender mesh object with shape_keys
        frames: List of AnimationFrame from gRPC response
        mapping: ARKit name -> Blender shape key name
        scene_fps: Blender scene FPS
        frame_offset: Starting frame number
        multipliers: Optional per-blendshape multiplier overrides

    Returns:
        Number of keyframes inserted
    """
    if not mesh_obj or not mesh_obj.data.shape_keys:
        return 0

    key_blocks = mesh_obj.data.shape_keys.key_blocks
    keyframes_inserted = 0

    for frame in frames:
        # Convert A2F timecode (seconds at 30 FPS) to Blender frame number
        blender_frame = frame.time_code * scene_fps + frame_offset

        for arkit_name, weight in frame.weights.items():
            blender_name = mapping.get(arkit_name, "")
            if not blender_name or blender_name not in key_blocks:
                continue

            # Apply multiplier if provided
            if multipliers and arkit_name in multipliers:
                weight *= multipliers[arkit_name]

            # Clamp to valid range
            weight = max(0.0, min(1.0, weight))

            kb = key_blocks[blender_name]
            kb.value = weight
            kb.keyframe_insert(data_path="value", frame=blender_frame)
            keyframes_inserted += 1

    # Set all inserted keyframes to LINEAR interpolation
    if mesh_obj.data.shape_keys.animation_data and mesh_obj.data.shape_keys.animation_data.action:
        action = mesh_obj.data.shape_keys.animation_data.action
        for fcurve in action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'LINEAR'

    return keyframes_inserted


def clear_animation(mesh_obj, mapping: dict[str, str]) -> int:
    """Remove A2F animation keyframes from mapped shape keys.

    Returns number of shape keys cleared.
    """
    if not mesh_obj or not mesh_obj.data.shape_keys:
        return 0

    key_blocks = mesh_obj.data.shape_keys.key_blocks
    shape_keys = mesh_obj.data.shape_keys
    cleared = 0

    if not shape_keys.animation_data or not shape_keys.animation_data.action:
        # No animation data, just reset values
        for arkit_name, blender_name in mapping.items():
            if blender_name and blender_name in key_blocks:
                key_blocks[blender_name].value = 0.0
                cleared += 1
        return cleared

    action = shape_keys.animation_data.action

    for arkit_name, blender_name in mapping.items():
        if not blender_name or blender_name not in key_blocks:
            continue

        # Find and remove the fcurve for this shape key
        data_path = f'key_blocks["{blender_name}"].value'
        fcurve = action.fcurves.find(data_path)
        if fcurve:
            action.fcurves.remove(fcurve)
            cleared += 1

        # Reset value
        key_blocks[blender_name].value = 0.0

    return cleared
