"""Shape key mapping: ARKit names <-> Blender mesh shape key names."""
from .. import constants

# VRM/VRChat name mapping to ARKit names
VRM_TO_ARKIT = {
    "Fcl_EYE_Close_L": "EyeBlinkLeft",
    "Fcl_EYE_Close_R": "EyeBlinkRight",
    "Fcl_EYE_Wide_L": "EyeWideLeft",
    "Fcl_EYE_Wide_R": "EyeWideRight",
    "Fcl_EYE_Squint_L": "EyeSquintLeft",
    "Fcl_EYE_Squint_R": "EyeSquintRight",
    "Fcl_BRW_Down_L": "BrowDownLeft",
    "Fcl_BRW_Down_R": "BrowDownRight",
    "Fcl_BRW_InnerUp": "BrowInnerUp",
    "Fcl_BRW_OuterUp_L": "BrowOuterUpLeft",
    "Fcl_BRW_OuterUp_R": "BrowOuterUpRight",
    "Fcl_MTH_A": "JawOpen",
    "Fcl_MTH_Close": "MouthClose",
    "Fcl_MTH_Funnel": "MouthFunnel",
    "Fcl_MTH_Pucker": "MouthPucker",
    "Fcl_MTH_Smile_L": "MouthSmileLeft",
    "Fcl_MTH_Smile_R": "MouthSmileRight",
    "Fcl_MTH_Frown_L": "MouthFrownLeft",
    "Fcl_MTH_Frown_R": "MouthFrownRight",
    "Fcl_MTH_LowerDown_L": "MouthLowerDownLeft",
    "Fcl_MTH_LowerDown_R": "MouthLowerDownRight",
    "Fcl_MTH_UpperUp_L": "MouthUpperUpLeft",
    "Fcl_MTH_UpperUp_R": "MouthUpperUpRight",
    "Fcl_MTH_ShrugLower": "MouthShrugLower",
    "Fcl_MTH_ShrugUpper": "MouthShrugUpper",
    "Fcl_MTH_Press_L": "MouthPressLeft",
    "Fcl_MTH_Press_R": "MouthPressRight",
    "Fcl_MTH_RollLower": "MouthRollLower",
    "Fcl_MTH_RollUpper": "MouthRollUpper",
    "Fcl_MTH_Stretch_L": "MouthStretchLeft",
    "Fcl_MTH_Stretch_R": "MouthStretchRight",
    "Fcl_MTH_Dimple_L": "MouthDimpleLeft",
    "Fcl_MTH_Dimple_R": "MouthDimpleRight",
    "Fcl_MTH_Left": "MouthLeft",
    "Fcl_MTH_Right": "MouthRight",
    "Fcl_JAW_Forward": "JawForward",
    "Fcl_JAW_Left": "JawLeft",
    "Fcl_JAW_Right": "JawRight",
    "Fcl_CHK_Puff": "CheekPuff",
    "Fcl_CHK_Squint_L": "CheekSquintLeft",
    "Fcl_CHK_Squint_R": "CheekSquintRight",
    "Fcl_NOSE_Sneer_L": "NoseSneerLeft",
    "Fcl_NOSE_Sneer_R": "NoseSneerRight",
}

# Invert for reverse lookup
ARKIT_TO_VRM = {v: k for k, v in VRM_TO_ARKIT.items()}


def auto_map(mesh_obj, preset: str = "ARKIT") -> dict[str, str]:
    """Auto-map ARKit blendshape names to shape keys on a mesh.

    Args:
        mesh_obj: Blender mesh object with shape_keys
        preset: 'ARKIT', 'VRM', or 'CUSTOM'

    Returns:
        dict mapping ARKit name -> Blender shape key name (or "" if unmapped)
    """
    if not mesh_obj or not mesh_obj.data.shape_keys:
        return {name: "" for name in constants.ARKIT_BLENDSHAPE_NAMES}

    # Get all shape key names (skip Basis)
    shape_key_names = [
        kb.name for kb in mesh_obj.data.shape_keys.key_blocks
        if kb.name != "Basis"
    ]

    # Build lowercase lookup
    lower_to_actual = {name.lower(): name for name in shape_key_names}

    mapping = {}
    for arkit_name in constants.ARKIT_BLENDSHAPE_NAMES:
        matched = ""

        if preset == "ARKIT":
            # Try exact case-insensitive match
            key = arkit_name.lower()
            if key in lower_to_actual:
                matched = lower_to_actual[key]

        elif preset == "VRM":
            # Try VRM name first
            vrm_name = ARKIT_TO_VRM.get(arkit_name, "")
            if vrm_name:
                key = vrm_name.lower()
                if key in lower_to_actual:
                    matched = lower_to_actual[key]
            # Fallback to ARKit name
            if not matched:
                key = arkit_name.lower()
                if key in lower_to_actual:
                    matched = lower_to_actual[key]

        else:  # CUSTOM -- try ARKit names as fallback
            key = arkit_name.lower()
            if key in lower_to_actual:
                matched = lower_to_actual[key]

        mapping[arkit_name] = matched

    return mapping


def count_mapped(mapping: dict[str, str]) -> tuple[int, int]:
    """Count mapped and total entries. Returns (mapped_count, total)."""
    mapped = sum(1 for v in mapping.values() if v)
    return mapped, len(mapping)
