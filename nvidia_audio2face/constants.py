"""Constants for Audio2Face addon: blendshape names, emotions, model configs, defaults."""

# 52 ARKit blendshape names in NVIDIA's exact order
ARKIT_BLENDSHAPE_NAMES = (
    "EyeBlinkLeft",
    "EyeLookDownLeft",
    "EyeLookInLeft",
    "EyeLookOutLeft",
    "EyeLookUpLeft",
    "EyeSquintLeft",
    "EyeWideLeft",
    "EyeBlinkRight",
    "EyeLookDownRight",
    "EyeLookInRight",
    "EyeLookOutRight",
    "EyeLookUpRight",
    "EyeSquintRight",
    "EyeWideRight",
    "JawForward",
    "JawLeft",
    "JawRight",
    "JawOpen",
    "MouthClose",
    "MouthFunnel",
    "MouthPucker",
    "MouthLeft",
    "MouthRight",
    "MouthSmileLeft",
    "MouthSmileRight",
    "MouthFrownLeft",
    "MouthFrownRight",
    "MouthDimpleLeft",
    "MouthDimpleRight",
    "MouthStretchLeft",
    "MouthStretchRight",
    "MouthRollLower",
    "MouthRollUpper",
    "MouthShrugLower",
    "MouthShrugUpper",
    "MouthPressLeft",
    "MouthPressRight",
    "MouthLowerDownLeft",
    "MouthLowerDownRight",
    "MouthUpperUpLeft",
    "MouthUpperUpRight",
    "BrowDownLeft",
    "BrowDownRight",
    "BrowInnerUp",
    "BrowOuterUpLeft",
    "BrowOuterUpRight",
    "CheekPuff",
    "CheekSquintLeft",
    "CheekSquintRight",
    "NoseSneerLeft",
    "NoseSneerRight",
)

# 10 emotion names in NVIDIA's order
EMOTION_NAMES = (
    "amazement",
    "anger",
    "cheekiness",
    "disgust",
    "fear",
    "grief",
    "joy",
    "outofbreath",
    "pain",
    "sadness",
)

# Cloud API function IDs per model
MODEL_FUNCTION_IDS = {
    "james_v2.3": "8082bdcb-9968-4dc5-8705-423ea98b8fc2",
    "james_v2.3_tongue": "9327c39f-a361-4e02-bd72-e11b4c9b7b5e",
    "claire_v2.3": "617f80a7-85e4-4bf0-9dd6-dcb61e886142",
    "claire_v2.3_tongue": "0961a6da-fb9e-4f2e-8491-247e5fd7bf8d",
    "mark_v2.3": "cf145b84-423b-4222-bfdd-15bb0142b0fd",
    "mark_v2.3_tongue": "8efc55f5-6f00-424e-afe9-26212cd2c630",
}

# Default face parameters (James model)
DEFAULT_FACE_PARAMS = {
    "upperFaceStrength": 1.0,
    "upperFaceSmoothing": 0.001,
    "lowerFaceStrength": 1.2,
    "lowerFaceSmoothing": 0.006,
    "faceMaskLevel": 0.6,
    "faceMaskSoftness": 0.0085,
    "skinStrength": 1.0,
    "eyelidOpenOffset": 0.06,
    "lipOpenOffset": -0.02,
}

# Default emotion post-processing parameters
DEFAULT_EMOTION_POST_PROCESSING = {
    "emotion_contrast": 1.0,
    "live_blend_coef": 0.7,
    "enable_preferred_emotion": False,
    "preferred_emotion_strength": 0.5,
    "emotion_strength": 0.6,
    "max_emotions": 3,
}

# Default blendshape weight multipliers (James model)
# Most are 1.0, these are the exceptions:
DEFAULT_WEIGHT_MULTIPLIERS = {name: 1.0 for name in ARKIT_BLENDSHAPE_NAMES}
# Zeroed (not animated by model)
for _name in (
    "EyeLookDownLeft", "EyeLookInLeft", "EyeLookOutLeft", "EyeLookUpLeft",
    "EyeLookDownRight", "EyeLookInRight", "EyeLookOutRight", "EyeLookUpRight",
):
    DEFAULT_WEIGHT_MULTIPLIERS[_name] = 0.0
# Reduced
DEFAULT_WEIGHT_MULTIPLIERS["JawLeft"] = 0.2
DEFAULT_WEIGHT_MULTIPLIERS["JawRight"] = 0.2
DEFAULT_WEIGHT_MULTIPLIERS["MouthLeft"] = 0.2
DEFAULT_WEIGHT_MULTIPLIERS["MouthRight"] = 0.2
DEFAULT_WEIGHT_MULTIPLIERS["MouthStretchLeft"] = 0.05
DEFAULT_WEIGHT_MULTIPLIERS["MouthStretchRight"] = 0.05
DEFAULT_WEIGHT_MULTIPLIERS["CheekPuff"] = 0.2
# Boosted
DEFAULT_WEIGHT_MULTIPLIERS["MouthSmileLeft"] = 1.2
DEFAULT_WEIGHT_MULTIPLIERS["MouthSmileRight"] = 1.2
DEFAULT_WEIGHT_MULTIPLIERS["BrowDownLeft"] = 1.2
DEFAULT_WEIGHT_MULTIPLIERS["BrowDownRight"] = 1.2
DEFAULT_WEIGHT_MULTIPLIERS["BrowInnerUp"] = 1.3

# Default blendshape weight offsets (all 0.0)
DEFAULT_WEIGHT_OFFSETS = {name: 0.0 for name in ARKIT_BLENDSHAPE_NAMES}

# Cloud API endpoint
CLOUD_ENDPOINT = "grpc.nvcf.nvidia.com:443"

# Default local server endpoint
DEFAULT_LOCAL_ENDPOINT = "localhost:52000"

# Audio constraints
AUDIO_SAMPLE_RATE = 16000
AUDIO_BITS_PER_SAMPLE = 16
AUDIO_MAX_DURATION_SECONDS = 300
AUDIO_MIN_DURATION_SECONDS = 0.1
AUDIO_CHUNK_SECONDS = 1

# Animation output FPS from A2F
A2F_OUTPUT_FPS = 30
