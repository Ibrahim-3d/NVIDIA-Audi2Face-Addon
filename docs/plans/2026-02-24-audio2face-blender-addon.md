# Audio2Face-3D Blender Addon — Full Implementation Plan (0 to 100)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete, shippable Blender addon that converts speech audio into 52 ARKit blendshape facial animations via NVIDIA's Audio2Face-3D gRPC API, with full UI, emotion controls, shape key mapping, and CSV import/export.

**Architecture:** Multi-file Blender extension (Python 3.11, Blender 4.2+) communicating with NVIDIA Audio2Face-3D via bidirectional gRPC streaming. Background thread runs asyncio gRPC client, main thread polls results via `bpy.app.timers` and applies keyframes. Protobuf stubs bundled from Maya-ACE (MIT). Wheels bundled for grpcio + protobuf.

**Tech Stack:** Python 3.11, Blender 4.2+ API (`bpy`), gRPC (`grpcio`), Protocol Buffers (`protobuf`), numpy (built into Blender), NVIDIA ACE protobuf stubs, stdlib `wave` + `csv` modules.

**Key Reference Documents:**
- `Audio2Face documentation.md` — Full NVIDIA API reference (gRPC protocol, data formats, models)
- `Blender documentation.md` — Blender addon development patterns (operators, panels, properties, timers)
- `roadmap.prd` — Feature specification, UI layouts, error handling, properties
- `plan.md` — Master plan with architecture decisions, competitive analysis, pricing

---

## Task 1: Create Addon Package Skeleton

**Files:**
- Create: `nvidia_audio2face/__init__.py`
- Create: `nvidia_audio2face/blender_manifest.toml`
- Create: `nvidia_audio2face/constants.py`
- Create: `nvidia_audio2face/properties.py` (empty placeholder)
- Create: `nvidia_audio2face/preferences.py` (empty placeholder)
- Create: `nvidia_audio2face/operators.py` (empty placeholder)
- Create: `nvidia_audio2face/panels.py` (empty placeholder)
- Create: `nvidia_audio2face/core/__init__.py` (empty)
- Create: `nvidia_audio2face/core/client.py` (empty placeholder)
- Create: `nvidia_audio2face/core/audio.py` (empty placeholder)
- Create: `nvidia_audio2face/core/mapping.py` (empty placeholder)
- Create: `nvidia_audio2face/core/animation.py` (empty placeholder)

**Step 1: Create directory structure**

```bash
mkdir -p nvidia_audio2face/core
mkdir -p nvidia_audio2face/vendor/nvidia_ace
mkdir -p nvidia_audio2face/wheels
```

**Step 2: Write `nvidia_audio2face/__init__.py`**

```python
bl_info = {
    "name": "Audio2Face for Blender",
    "author": "Ibrahim",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Audio2Face",
    "description": "AI-powered facial animation from audio using NVIDIA Audio2Face-3D",
    "category": "Animation",
}

import importlib
import sys
import os

# Add vendor directory to path for nvidia_ace stubs
_vendor_path = os.path.join(os.path.dirname(__file__), "vendor")
if _vendor_path not in sys.path:
    sys.path.insert(0, _vendor_path)

from . import constants
from . import properties
from . import preferences
from . import operators
from . import panels

_modules = [constants, properties, preferences, operators, panels]


def register():
    for mod in _modules:
        if hasattr(mod, "register"):
            mod.register()


def unregister():
    for mod in reversed(_modules):
        if hasattr(mod, "unregister"):
            mod.unregister()


if __name__ == "__main__":
    register()
```

**Step 3: Write `nvidia_audio2face/blender_manifest.toml`**

```toml
schema_version = "1.0.0"

id = "nvidia_audio2face"
version = "1.0.0"
name = "Audio2Face for Blender"
tagline = "AI-powered facial animation from audio using NVIDIA Audio2Face-3D"
maintainer = "Ibrahim"
type = "add-on"

website = ""

tags = ["Animation", "Rigging"]

blender_version_min = "4.2.0"

license = ["SPDX:GPL-3.0-or-later"]

[permissions]
network = "Connect to NVIDIA Audio2Face-3D service for AI facial animation generation"
files = "Read audio WAV files and export animation CSV data"

# wheels = [
#     "./wheels/grpcio-1.64.1-cp311-cp311-manylinux_2_17_x86_64.whl",
#     "./wheels/grpcio-1.64.1-cp311-cp311-win_amd64.whl",
#     "./wheels/grpcio-1.64.1-cp311-cp311-macosx_10_9_universal2.whl",
#     "./wheels/protobuf-5.27.0-cp311-cp311-manylinux2014_x86_64.whl",
#     "./wheels/protobuf-5.27.0-cp311-cp311-win_amd64.whl",
#     "./wheels/protobuf-5.27.0-cp311-cp311-macosx_10_9_universal2.whl",
# ]
```

**Step 4: Write empty placeholder modules**

Each placeholder should contain just a docstring and empty register/unregister:

```python
# nvidia_audio2face/properties.py
"""Scene property group for Audio2Face addon state."""


def register():
    pass


def unregister():
    pass
```

Same pattern for: `preferences.py`, `operators.py`, `panels.py`.

For `core/__init__.py`, `core/client.py`, `core/audio.py`, `core/mapping.py`, `core/animation.py` — just an empty file or docstring.

**Step 5: Commit**

```bash
git add nvidia_audio2face/
git commit -m "feat: create addon package skeleton with directory structure"
```

---

## Task 2: Implement constants.py

**Files:**
- Modify: `nvidia_audio2face/constants.py`

**Step 1: Write constants.py with all data**

```python
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
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/constants.py
git commit -m "feat: add constants with 52 ARKit blendshapes, emotions, model configs"
```

---

## Task 3: Set Up nvidia_ace Protobuf Stubs

**Files:**
- Create: `nvidia_audio2face/vendor/nvidia_ace/` (full directory with proto stubs)

**Step 1: Clone Maya-ACE and extract stubs**

```bash
# Clone Maya-ACE repo temporarily to get protobuf stubs
git clone --depth 1 https://github.com/NVIDIA/Maya-ACE.git /tmp/maya-ace

# Copy nvidia_ace stubs
cp -r /tmp/maya-ace/python/grpc_py/nvidia_ace/* nvidia_audio2face/vendor/nvidia_ace/

# Clean up
rm -rf /tmp/maya-ace
```

**Step 2: Verify stubs load**

Check that the following files exist:
- `vendor/nvidia_ace/__init__.py`
- `vendor/nvidia_ace/a2f/v1_pb2.py`
- `vendor/nvidia_ace/audio/v1_pb2.py`
- `vendor/nvidia_ace/controller/v1_pb2.py`
- `vendor/nvidia_ace/animation_data/v1_pb2.py`
- `vendor/nvidia_ace/emotion_with_timecode/v1_pb2.py`
- `vendor/nvidia_ace/status/v1_pb2.py`
- `vendor/nvidia_ace/services/a2f_controller/v1_pb2_grpc.py`

If `Maya-ACE` doesn't have the stubs at that path, check the `Audio2Face-3D-Samples` repo instead:
```bash
git clone --depth 1 https://github.com/NVIDIA/Audio2Face-3D-Samples.git /tmp/a2f-samples
# Look for proto stubs in python/ or protos/ directory
```

**Step 3: Create `__init__.py` files if missing**

Ensure every subdirectory under `vendor/nvidia_ace/` has an `__init__.py`.

**Step 4: Commit**

```bash
git add nvidia_audio2face/vendor/
git commit -m "feat: add nvidia_ace protobuf stubs from Maya-ACE (MIT licensed)"
```

---

## Task 4: Download and Bundle gRPC Wheels

**Files:**
- Create: `nvidia_audio2face/wheels/` (wheel files)

**Step 1: Download grpcio wheels for Blender's Python 3.11**

```bash
pip download grpcio==1.64.1 \
  --python-version 311 \
  --only-binary=:all: \
  --platform manylinux_2_17_x86_64 \
  --platform win_amd64 \
  --platform macosx_10_9_universal2 \
  -d nvidia_audio2face/wheels/
```

**Step 2: Download protobuf wheels**

```bash
pip download protobuf==5.27.0 \
  --python-version 311 \
  --only-binary=:all: \
  -d nvidia_audio2face/wheels/
```

**Step 3: Verify wheels exist**

Should have ~6 wheel files (grpcio for 3 platforms + protobuf for 3 platforms).

**Step 4: Update `blender_manifest.toml` to reference wheels**

Uncomment the wheels section and update with actual filenames.

**Step 5: Add wheels to .gitignore or git LFS**

Wheels are large binary files. Either:
- Add to `.gitignore` and distribute separately, OR
- Use `git lfs track "*.whl"` and commit

**Step 6: Commit**

```bash
git add nvidia_audio2face/wheels/ nvidia_audio2face/blender_manifest.toml
git commit -m "feat: bundle grpcio and protobuf wheels for cross-platform support"
```

---

## Task 5: Implement Addon Preferences

**Files:**
- Modify: `nvidia_audio2face/preferences.py`

**Step 1: Write preferences.py**

```python
"""Addon preferences — API key, server URL, default settings."""
import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty

from . import constants


class A2F_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    api_key: StringProperty(
        name="API Key",
        description="NVIDIA API key from build.nvidia.com",
        subtype='PASSWORD',
        default="",
    )

    default_model: EnumProperty(
        name="Default Model",
        description="Default Audio2Face-3D model for generation",
        items=[
            ('james_v2.3', "James v2.3", "English male, strong emotion expression"),
            ('claire_v2.3', "Claire v2.3", "Chinese + English female voice"),
            ('mark_v2.3', "Mark v2.3", "English male, high-resolution geometry"),
        ],
        default='james_v2.3',
    )

    connection_mode: EnumProperty(
        name="Default Connection",
        description="Default connection mode for Audio2Face service",
        items=[
            ('CLOUD', "Cloud API", "Use NVIDIA cloud API (grpc.nvcf.nvidia.com)"),
            ('LOCAL', "Local Server", "Connect to a local NIM server"),
        ],
        default='CLOUD',
    )

    server_url: StringProperty(
        name="Local Server URL",
        description="Address of local Audio2Face-3D NIM server (host:port)",
        default=constants.DEFAULT_LOCAL_ENDPOINT,
    )

    auto_create_shapekeys: BoolProperty(
        name="Auto-Create Shape Keys",
        description="Automatically create missing ARKit shape keys on target mesh",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.prop(self, "default_model")
        layout.prop(self, "connection_mode")
        if self.connection_mode == 'LOCAL':
            layout.prop(self, "server_url")
        layout.prop(self, "auto_create_shapekeys")


_classes = (A2F_AP_preferences,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/preferences.py
git commit -m "feat: add addon preferences with API key, model, connection settings"
```

---

## Task 6: Implement Properties (Scene State)

**Files:**
- Modify: `nvidia_audio2face/properties.py`

**Step 1: Write properties.py with full property group**

```python
"""Scene properties for Audio2Face addon state."""
import bpy
from bpy.props import (
    StringProperty, PointerProperty, EnumProperty, IntProperty,
    FloatProperty, BoolProperty, CollectionProperty,
)


class A2F_PG_mapping_item(bpy.types.PropertyGroup):
    """Single ARKit-to-Blender shape key mapping entry."""
    arkit_name: StringProperty(name="ARKit Name")
    blender_name: StringProperty(name="Blender Shape Key", default="")
    enabled: BoolProperty(name="Enabled", default=True)
    multiplier: FloatProperty(name="Multiplier", default=1.0, min=0.0, max=5.0)


class A2F_PG_properties(bpy.types.PropertyGroup):
    """Main property group stored on bpy.types.Scene."""

    # ── Core Settings ──
    audio_file: StringProperty(
        name="Audio File",
        description="Path to WAV audio file (PCM 16-bit, mono or stereo)",
        subtype='FILE_PATH',
        default="",
    )
    target_mesh: PointerProperty(
        name="Target Mesh",
        description="Mesh object to apply facial animation to",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )
    model: EnumProperty(
        name="Model",
        description="Audio2Face-3D model to use",
        items=[
            ('james_v2.3', "James v2.3", "English male, strong emotion expression"),
            ('claire_v2.3', "Claire v2.3", "Chinese + English female voice"),
            ('mark_v2.3', "Mark v2.3", "English male, high-resolution geometry"),
        ],
        default='james_v2.3',
    )
    frame_start: IntProperty(
        name="Frame Start",
        description="Frame number where animation begins on the timeline",
        default=1,
        min=0,
    )

    # ── Generation State (transient) ──
    is_generating: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})
    generation_progress: FloatProperty(
        default=0.0, min=0.0, max=1.0, subtype='FACTOR',
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    last_status: StringProperty(default="Ready", options={'SKIP_SAVE'})
    last_frame_count: IntProperty(default=0, options={'SKIP_SAVE'})

    # ── Connection ──
    connection_mode: EnumProperty(
        name="Connection Mode",
        items=[
            ('CLOUD', "Cloud API", "Use NVIDIA cloud API (grpc.nvcf.nvidia.com)"),
            ('LOCAL', "Local Server", "Connect to a local NIM server"),
        ],
        default='CLOUD',
    )
    server_url: StringProperty(
        name="Server URL",
        description="Address of local Audio2Face-3D NIM server",
        default="localhost:52000",
    )

    # ── Emotion Controls ──
    auto_emotion: BoolProperty(
        name="Auto-Detect Emotion",
        description="Let Audio2Emotion detect emotion from audio automatically",
        default=True,
    )
    emotion_strength: FloatProperty(
        name="Emotion Strength", default=0.6, min=0.0, max=2.0, step=10,
    )
    emotion_contrast: FloatProperty(
        name="Emotion Contrast", default=1.0, min=0.0, max=3.0, step=10,
    )
    max_emotions: IntProperty(
        name="Max Emotions", default=3, min=1, max=10,
    )

    # Manual emotion overrides
    emotion_joy: FloatProperty(name="Joy", default=0.0, min=0.0, max=1.0, step=10)
    emotion_anger: FloatProperty(name="Anger", default=0.0, min=0.0, max=1.0, step=10)
    emotion_sadness: FloatProperty(name="Sadness", default=0.0, min=0.0, max=1.0, step=10)
    emotion_fear: FloatProperty(name="Fear", default=0.0, min=0.0, max=1.0, step=10)
    emotion_amazement: FloatProperty(name="Amazement", default=0.0, min=0.0, max=1.0, step=10)
    emotion_disgust: FloatProperty(name="Disgust", default=0.0, min=0.0, max=1.0, step=10)
    emotion_cheekiness: FloatProperty(name="Cheekiness", default=0.0, min=0.0, max=1.0, step=10)
    emotion_grief: FloatProperty(name="Grief", default=0.0, min=0.0, max=1.0, step=10)
    emotion_pain: FloatProperty(name="Pain", default=0.0, min=0.0, max=1.0, step=10)
    emotion_outofbreath: FloatProperty(name="Out of Breath", default=0.0, min=0.0, max=1.0, step=10)

    # ── Face Parameters ──
    skin_strength: FloatProperty(name="Skin Strength", default=1.0, min=0.0, max=3.0, step=10)
    upper_face_strength: FloatProperty(name="Upper Face Strength", default=1.0, min=0.0, max=3.0, step=10)
    upper_face_smoothing: FloatProperty(name="Upper Face Smoothing", default=0.001, min=0.0, max=0.1, step=1, precision=4)
    lower_face_strength: FloatProperty(name="Lower Face Strength", default=1.2, min=0.0, max=3.0, step=10)
    lower_face_smoothing: FloatProperty(name="Lower Face Smoothing", default=0.006, min=0.0, max=0.1, step=1, precision=4)
    face_mask_level: FloatProperty(name="Face Mask Level", default=0.6, min=0.0, max=1.0, step=10)
    face_mask_softness: FloatProperty(name="Face Mask Softness", default=0.0085, min=0.0, max=0.1, step=1, precision=4)
    eyelid_open_offset: FloatProperty(name="Eyelid Open Offset", default=0.06, min=-0.5, max=0.5, step=1)
    lip_open_offset: FloatProperty(name="Lip Open Offset", default=-0.02, min=-0.5, max=0.5, step=1)

    # ── Mapping ──
    mapping_preset: EnumProperty(
        name="Mapping Preset",
        items=[
            ('ARKIT', "ARKit (Standard)", "Standard ARKit blendshape names"),
            ('VRM', "VRM / VRChat", "VRM blendshape naming convention"),
            ('CUSTOM', "Custom", "Use custom name mapping"),
        ],
        default='ARKIT',
    )
    mapping_items: CollectionProperty(type=A2F_PG_mapping_item)
    mapping_items_index: IntProperty(default=0)


_classes = (A2F_PG_mapping_item, A2F_PG_properties)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.a2f_props = PointerProperty(type=A2F_PG_properties)


def unregister():
    del bpy.types.Scene.a2f_props
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/properties.py
git commit -m "feat: add scene properties with emotion, face params, and mapping"
```

---

## Task 7: Implement Audio Processing Module

**Files:**
- Modify: `nvidia_audio2face/core/audio.py`

**Step 1: Write core/audio.py**

```python
"""Audio loading, validation, resampling, and chunking."""
import wave
import struct
from pathlib import Path
from typing import Optional

import numpy as np

from .. import constants


class AudioError(Exception):
    """Raised when audio validation or processing fails."""
    pass


def load_wav(filepath: str) -> tuple[int, np.ndarray, int]:
    """Load a WAV file and return (sample_rate, data_int16, num_channels).

    Raises AudioError if the file is invalid or unsupported.
    """
    path = Path(filepath)
    if not path.exists():
        raise AudioError(f"Audio file not found: {filepath}")
    if path.suffix.lower() != ".wav":
        raise AudioError("Unsupported audio format. Please use WAV (PCM 16-bit).")

    try:
        with wave.open(str(path), "rb") as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            num_frames = wf.getnframes()

            if sample_width != 2:
                raise AudioError(
                    f"Audio must be 16-bit PCM WAV. Current: {sample_width * 8}-bit"
                )
            if num_channels > 2:
                raise AudioError(
                    f"Only mono or stereo audio supported. File has {num_channels} channels."
                )

            raw_data = wf.readframes(num_frames)
    except wave.Error as e:
        raise AudioError(f"Cannot read WAV file: {e}")

    # Convert bytes to int16 numpy array
    total_samples = num_frames * num_channels
    data = np.frombuffer(raw_data, dtype=np.int16)

    return sample_rate, data, num_channels


def convert_to_mono(data: np.ndarray, num_channels: int) -> np.ndarray:
    """Convert stereo audio to mono by averaging channels."""
    if num_channels == 1:
        return data
    # Interleaved stereo: L0 R0 L1 R1 ...
    left = data[0::2].astype(np.int32)
    right = data[1::2].astype(np.int32)
    return ((left + right) // 2).astype(np.int16)


def resample(data: np.ndarray, original_rate: int, target_rate: int = 16000) -> np.ndarray:
    """Resample audio using linear interpolation (numpy only, no scipy)."""
    if original_rate == target_rate:
        return data
    ratio = target_rate / original_rate
    new_length = int(len(data) * ratio)
    if new_length == 0:
        return data
    x_old = np.linspace(0, 1, len(data))
    x_new = np.linspace(0, 1, new_length)
    return np.interp(x_new, x_old, data.astype(np.float64)).astype(np.int16)


def validate_duration(data: np.ndarray, sample_rate: int) -> None:
    """Validate audio duration is within acceptable range."""
    duration = len(data) / sample_rate
    if duration > constants.AUDIO_MAX_DURATION_SECONDS:
        raise AudioError(
            f"Audio exceeds 5 minute limit ({duration:.1f}s). Please use a shorter clip."
        )
    if duration < constants.AUDIO_MIN_DURATION_SECONDS:
        raise AudioError(
            f"Audio too short ({duration:.3f}s). Minimum is 0.1 seconds."
        )


def chunk_audio(data: np.ndarray, sample_rate: int) -> list[bytes]:
    """Split audio into 1-second chunks as PCM16 bytes."""
    chunk_size = sample_rate * constants.AUDIO_CHUNK_SECONDS
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        if len(chunk) > 0:
            chunks.append(chunk.tobytes())
    return chunks


def process_audio(filepath: str) -> tuple[list[bytes], int, list[str]]:
    """Full audio processing pipeline.

    Returns (chunks, sample_rate, info_messages).
    info_messages contains user-facing info about conversions performed.
    """
    info_messages = []

    # Load
    sample_rate, data, num_channels = load_wav(filepath)

    # Convert to mono
    if num_channels == 2:
        data = convert_to_mono(data, num_channels)
        info_messages.append("Stereo audio auto-converted to mono.")

    # Resample if needed
    target_rate = constants.AUDIO_SAMPLE_RATE
    if sample_rate not in (16000, 32000, 48000):
        original_rate = sample_rate
        data = resample(data, sample_rate, target_rate)
        sample_rate = target_rate
        info_messages.append(f"Audio resampled from {original_rate}Hz to {target_rate}Hz.")
    elif sample_rate != target_rate:
        # Accept 32k and 48k as-is, but use 16k for chunking math
        pass

    # Validate duration
    validate_duration(data, sample_rate)

    # Chunk
    chunks = chunk_audio(data, sample_rate)

    return chunks, sample_rate, info_messages
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/core/audio.py
git commit -m "feat: add audio loading, validation, resampling, and chunking"
```

---

## Task 8: Implement gRPC Client

**Files:**
- Modify: `nvidia_audio2face/core/client.py`

**Step 1: Write core/client.py with full gRPC client**

```python
"""gRPC client for NVIDIA Audio2Face-3D service."""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

import grpc

from .. import constants

# Import nvidia_ace protobuf stubs (from vendor/)
from nvidia_ace.services.a2f_controller import v1_pb2_grpc as a2f_controller_grpc
from nvidia_ace.controller import v1_pb2 as controller_pb2
from nvidia_ace.audio import v1_pb2 as audio_pb2
from nvidia_ace.a2f import v1_pb2 as a2f_pb2
from nvidia_ace.animation_data import v1_pb2 as animation_pb2
from nvidia_ace.emotion_with_timecode import v1_pb2 as emotion_pb2
from nvidia_ace.status import v1_pb2 as status_pb2

logger = logging.getLogger(__name__)


@dataclass
class AnimationFrame:
    """Single frame of animation data."""
    time_code: float
    weights: dict[str, float]  # {blendshape_name: weight_value}


@dataclass
class GenerationState:
    """Thread-safe state shared between background thread and main thread."""
    status: str = "idle"  # idle, connecting, streaming, receiving, done, error
    progress: float = 0.0  # 0.0 to 1.0
    error_message: str = ""
    blendshape_names: list[str] = field(default_factory=list)
    animation_frames: list[AnimationFrame] = field(default_factory=list)
    emotion_data: list[dict] = field(default_factory=list)


def create_cloud_channel(api_key: str, function_id: str) -> grpc.aio.Channel:
    """Create authenticated gRPC channel to NVIDIA cloud."""
    ssl_creds = grpc.ssl_channel_credentials()

    def metadata_callback(context, callback):
        callback([
            ("function-id", function_id),
            ("authorization", f"Bearer {api_key}"),
        ], None)

    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    composite_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)

    return grpc.aio.secure_channel(
        constants.CLOUD_ENDPOINT,
        composite_creds,
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )


def create_local_channel(server_url: str) -> grpc.aio.Channel:
    """Create insecure gRPC channel to local NIM server."""
    return grpc.aio.insecure_channel(
        server_url,
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )


def _build_audio_stream_header(
    sample_rate: int,
    face_params: dict,
    emotion_params: dict,
    weight_multipliers: dict,
    weight_offsets: dict,
) -> controller_pb2.AudioStream:
    """Build the first gRPC message (AudioStreamHeader)."""
    header = controller_pb2.AudioStreamHeader(
        audio_header=audio_pb2.AudioHeader(
            samples_per_second=sample_rate,
            bits_per_sample=constants.AUDIO_BITS_PER_SAMPLE,
            channel_count=1,
            audio_format=audio_pb2.AUDIO_FORMAT_PCM,
        ),
        face_params=a2f_pb2.FaceParameters(
            float_params=face_params,
        ),
        emotion_post_processing_params=a2f_pb2.EmotionPostProcessingParameters(
            emotion_contrast=emotion_params.get("emotion_contrast", 1.0),
            live_blend_coef=emotion_params.get("live_blend_coef", 0.7),
            enable_preferred_emotion=emotion_params.get("enable_preferred_emotion", False),
            preferred_emotion_strength=emotion_params.get("preferred_emotion_strength", 0.5),
            emotion_strength=emotion_params.get("emotion_strength", 0.6),
            max_emotions=emotion_params.get("max_emotions", 3),
        ),
        blendshape_params=a2f_pb2.BlendShapeParameters(
            bs_weight_multipliers=weight_multipliers,
            bs_weight_offsets=weight_offsets,
            enable_clamping_bs_weight=False,
        ),
        emotion_params=a2f_pb2.EmotionParameters(
            live_transition_time=0.0001,
        ),
    )
    return controller_pb2.AudioStream(audio_stream_header=header)


def _build_audio_chunk_message(
    audio_bytes: bytes,
    emotions: Optional[dict] = None,
    time_code: float = 0.0,
) -> controller_pb2.AudioStream:
    """Build an audio data chunk message."""
    emotion_list = []
    if emotions:
        emotion_msg = emotion_pb2.Emotion(**emotions)
        emotion_list.append(
            emotion_pb2.EmotionWithTimeCode(emotion=emotion_msg, time_code=time_code)
        )

    audio_with_emotion = a2f_pb2.AudioWithEmotion(
        audio_buffer=audio_bytes,
        emotions=emotion_list,
    )
    return controller_pb2.AudioStream(audio_with_emotion=audio_with_emotion)


def _build_end_of_audio() -> controller_pb2.AudioStream:
    """Build the EndOfAudio termination message."""
    return controller_pb2.AudioStream(
        end_of_audio=controller_pb2.EndOfAudio()
    )


async def generate_animation(
    channel: grpc.aio.Channel,
    audio_chunks: list[bytes],
    sample_rate: int,
    face_params: dict,
    emotion_params: dict,
    weight_multipliers: dict,
    weight_offsets: dict,
    manual_emotions: Optional[dict] = None,
    state: Optional[GenerationState] = None,
) -> GenerationState:
    """Run the full generation pipeline via bidirectional gRPC streaming.

    Args:
        channel: gRPC channel (cloud or local)
        audio_chunks: List of PCM16 audio bytes (1 second each)
        sample_rate: Audio sample rate
        face_params: FaceParameters dict
        emotion_params: EmotionPostProcessingParameters dict
        weight_multipliers: Per-blendshape multipliers dict
        weight_offsets: Per-blendshape offsets dict
        manual_emotions: Optional emotion override dict
        state: GenerationState to update (created if None)

    Returns:
        GenerationState with results
    """
    if state is None:
        state = GenerationState()

    state.status = "connecting"
    state.progress = 0.0

    stub = a2f_controller_grpc.A2FControllerServiceStub(channel)

    async def _send_stream():
        """Generator that yields audio stream messages."""
        # 1. Send header
        yield _build_audio_stream_header(
            sample_rate, face_params, emotion_params,
            weight_multipliers, weight_offsets,
        )

        state.status = "streaming"
        total_chunks = len(audio_chunks)

        # 2. Send audio chunks
        for i, chunk in enumerate(audio_chunks):
            emotions = manual_emotions if i == 0 and manual_emotions else None
            yield _build_audio_chunk_message(chunk, emotions)
            state.progress = (i + 1) / total_chunks * 0.5

        # 3. Send end of audio
        yield _build_end_of_audio()

    try:
        stream = stub.ProcessAudioStream(_send_stream())

        state.status = "receiving"
        estimated_frames = len(audio_chunks) * constants.A2F_OUTPUT_FPS
        frames_received = 0

        async for response in stream:
            # Handle header
            if response.HasField("animation_data_stream_header"):
                header = response.animation_data_stream_header
                if header.skel_animation_header.blend_shapes:
                    state.blendshape_names = list(
                        header.skel_animation_header.blend_shapes
                    )

            # Handle animation data
            elif response.HasField("animation_data"):
                anim = response.animation_data
                if anim.skel_animation and anim.skel_animation.blend_shape_weights:
                    bsw = anim.skel_animation.blend_shape_weights
                    # May be a single frame or batch
                    if hasattr(bsw, '__iter__') and not hasattr(bsw, 'time_code'):
                        # Batch of frames
                        for frame_data in bsw:
                            weights = {}
                            for j, val in enumerate(frame_data.values):
                                if j < len(state.blendshape_names):
                                    weights[state.blendshape_names[j]] = val
                            state.animation_frames.append(
                                AnimationFrame(
                                    time_code=frame_data.time_code,
                                    weights=weights,
                                )
                            )
                            frames_received += 1
                    else:
                        # Single frame
                        weights = {}
                        for j, val in enumerate(bsw.values):
                            if j < len(state.blendshape_names):
                                weights[state.blendshape_names[j]] = val
                        state.animation_frames.append(
                            AnimationFrame(time_code=bsw.time_code, weights=weights)
                        )
                        frames_received += 1

                    if estimated_frames > 0:
                        state.progress = 0.5 + (frames_received / estimated_frames) * 0.5

            # Handle status
            elif response.HasField("status"):
                resp_status = response.status
                if resp_status.code == 0:  # SUCCESS
                    state.status = "done"
                    state.progress = 1.0
                elif resp_status.code == 3:  # ERROR
                    state.status = "error"
                    state.error_message = f"Server error: {resp_status.message}"

        if state.status == "receiving":
            state.status = "done"
            state.progress = 1.0

    except grpc.aio.AioRpcError as e:
        state.status = "error"
        code = e.code()
        if code == grpc.StatusCode.UNAUTHENTICATED:
            state.error_message = "Invalid API key. Get one free at build.nvidia.com"
        elif code == grpc.StatusCode.UNAVAILABLE:
            state.error_message = "Cannot connect to Audio2Face service. Check your network/server."
        elif code == grpc.StatusCode.RESOURCE_EXHAUSTED:
            state.error_message = "API credits may be exhausted. Check your NVIDIA account."
        elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
            state.error_message = "Connection timed out. Check your network/server."
        else:
            state.error_message = f"gRPC error ({code.name}): {e.details()}"
        logger.error("gRPC error: %s - %s", code, e.details())
    except Exception as e:
        state.status = "error"
        state.error_message = f"Unexpected error: {e}"
        logger.exception("Unexpected error in generation")

    return state


async def health_check(channel: grpc.aio.Channel, timeout: float = 5.0) -> tuple[bool, str]:
    """Check if the Audio2Face service is reachable.

    Returns (success, message).
    """
    try:
        # Try a minimal stream to verify connectivity
        stub = a2f_controller_grpc.A2FControllerServiceStub(channel)
        # We can't easily do a health check without sending audio,
        # so we just check if the channel connects
        await asyncio.wait_for(
            channel.channel_ready(),
            timeout=timeout,
        )
        return True, "Successfully connected to Audio2Face service."
    except asyncio.TimeoutError:
        return False, f"Connection timed out after {timeout:.0f} seconds."
    except grpc.aio.AioRpcError as e:
        code = e.code()
        if code == grpc.StatusCode.UNAUTHENTICATED:
            return False, "Authentication failed. Check your API key."
        return False, f"Connection failed: {e.details()}"
    except Exception as e:
        return False, f"Connection failed: {e}"
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/core/client.py
git commit -m "feat: add gRPC client with bidirectional streaming and health check"
```

---

## Task 9: Implement Shape Key Mapping Module

**Files:**
- Modify: `nvidia_audio2face/core/mapping.py`

**Step 1: Write core/mapping.py**

```python
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
    mapping = {}

    if not mesh_obj or not mesh_obj.data.shape_keys:
        return {name: "" for name in constants.ARKIT_BLENDSHAPE_NAMES}

    # Get all shape key names (skip Basis)
    shape_key_names = [
        kb.name for kb in mesh_obj.data.shape_keys.key_blocks
        if kb.name != "Basis"
    ]

    # Build lowercase lookup
    lower_to_actual = {name.lower(): name for name in shape_key_names}

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

        else:  # CUSTOM — try ARKit names as fallback
            key = arkit_name.lower()
            if key in lower_to_actual:
                matched = lower_to_actual[key]

        mapping[arkit_name] = matched

    return mapping


def count_mapped(mapping: dict[str, str]) -> tuple[int, int]:
    """Count mapped and total entries. Returns (mapped_count, total)."""
    mapped = sum(1 for v in mapping.values() if v)
    return mapped, len(mapping)
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/core/mapping.py
git commit -m "feat: add shape key mapping with ARKit and VRM presets"
```

---

## Task 10: Implement Animation Module

**Files:**
- Modify: `nvidia_audio2face/core/animation.py`

**Step 1: Write core/animation.py**

```python
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
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/core/animation.py
git commit -m "feat: add animation keyframe insertion and clearing"
```

---

## Task 11: Implement All Operators

**Files:**
- Modify: `nvidia_audio2face/operators.py`

**Step 1: Write operators.py with all operators**

```python
"""Blender operators for Audio2Face addon."""
import asyncio
import csv
import threading
from pathlib import Path

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import constants
from .core import audio, client, mapping, animation


# Thread-safe storage for generation state
_generation_state: client.GenerationState | None = None
_generation_thread: threading.Thread | None = None


def _get_prefs():
    """Get addon preferences."""
    return bpy.context.preferences.addons[__package__].preferences


def _get_props(context):
    """Get scene properties."""
    return context.scene.a2f_props


def _build_face_params(props) -> dict:
    """Build face parameters dict from scene properties."""
    return {
        "upperFaceStrength": props.upper_face_strength,
        "upperFaceSmoothing": props.upper_face_smoothing,
        "lowerFaceStrength": props.lower_face_strength,
        "lowerFaceSmoothing": props.lower_face_smoothing,
        "faceMaskLevel": props.face_mask_level,
        "faceMaskSoftness": props.face_mask_softness,
        "skinStrength": props.skin_strength,
        "eyelidOpenOffset": props.eyelid_open_offset,
        "lipOpenOffset": props.lip_open_offset,
    }


def _build_emotion_params(props) -> dict:
    """Build emotion post-processing parameters from scene properties."""
    return {
        "emotion_contrast": props.emotion_contrast,
        "live_blend_coef": 0.7,
        "enable_preferred_emotion": not props.auto_emotion,
        "preferred_emotion_strength": 0.5,
        "emotion_strength": props.emotion_strength,
        "max_emotions": props.max_emotions,
    }


def _build_manual_emotions(props) -> dict | None:
    """Build manual emotion override dict, or None if auto."""
    if props.auto_emotion:
        return None
    emotions = {
        "amazement": props.emotion_amazement,
        "anger": props.emotion_anger,
        "cheekiness": props.emotion_cheekiness,
        "disgust": props.emotion_disgust,
        "fear": props.emotion_fear,
        "grief": props.emotion_grief,
        "joy": props.emotion_joy,
        "outofbreath": props.emotion_outofbreath,
        "pain": props.emotion_pain,
        "sadness": props.emotion_sadness,
    }
    # Only send if at least one emotion is set
    if any(v > 0.0 for v in emotions.values()):
        return emotions
    return None


def _build_mapping(props) -> dict[str, str]:
    """Build mapping dict from mapping_items or auto-map."""
    if props.mapping_items:
        return {
            item.arkit_name: item.blender_name
            for item in props.mapping_items
            if item.enabled
        }
    # Fallback: auto-map
    if props.target_mesh:
        return mapping.auto_map(props.target_mesh, props.mapping_preset)
    return {}


def _build_multipliers(props) -> dict[str, float]:
    """Build per-blendshape multipliers from mapping_items."""
    mults = {}
    for item in props.mapping_items:
        if item.enabled:
            mults[item.arkit_name] = item.multiplier
    return mults if mults else None


def _run_generation(
    mode: str,
    api_key: str,
    function_id: str,
    server_url: str,
    audio_chunks: list[bytes],
    sample_rate: int,
    face_params: dict,
    emotion_params: dict,
    weight_multipliers: dict,
    weight_offsets: dict,
    manual_emotions: dict | None,
    state: client.GenerationState,
):
    """Background thread entry point for generation."""
    async def _async_generate():
        if mode == "CLOUD":
            channel = client.create_cloud_channel(api_key, function_id)
        else:
            channel = client.create_local_channel(server_url)

        try:
            await client.generate_animation(
                channel=channel,
                audio_chunks=audio_chunks,
                sample_rate=sample_rate,
                face_params=face_params,
                emotion_params=emotion_params,
                weight_multipliers=weight_multipliers,
                weight_offsets=weight_offsets,
                manual_emotions=manual_emotions,
                state=state,
            )
        finally:
            await channel.close()

    asyncio.run(_async_generate())


def _poll_generation():
    """Timer callback that polls generation state and applies results."""
    global _generation_state, _generation_thread

    if _generation_state is None:
        return None  # Unregister timer

    scene = bpy.context.scene
    props = scene.a2f_props
    wm = bpy.context.window_manager

    # Update progress
    props.generation_progress = _generation_state.progress

    if _generation_state.status == "done":
        # Apply animation
        mesh_obj = props.target_mesh
        if mesh_obj and _generation_state.animation_frames:
            mapping_dict = _build_mapping(props)
            multipliers = _build_multipliers(props)

            num_keyframes = animation.apply_animation(
                mesh_obj=mesh_obj,
                frames=_generation_state.animation_frames,
                mapping=mapping_dict,
                scene_fps=scene.render.fps,
                frame_offset=props.frame_start,
                multipliers=multipliers,
            )

            num_frames = len(_generation_state.animation_frames)
            duration = num_frames / constants.A2F_OUTPUT_FPS
            props.last_status = f"Generated {num_frames} frames ({duration:.1f}s)"
            props.last_frame_count = num_frames
        else:
            props.last_status = "Generation completed but no data received"

        props.is_generating = False
        wm.progress_end()
        _generation_state = None
        _generation_thread = None

        # Force UI update
        for area in bpy.context.screen.areas:
            area.tag_redraw()

        return None  # Unregister timer

    elif _generation_state.status == "error":
        props.last_status = f"Error: {_generation_state.error_message}"
        props.is_generating = False
        wm.progress_end()
        _generation_state = None
        _generation_thread = None

        for area in bpy.context.screen.areas:
            area.tag_redraw()

        return None  # Unregister timer

    else:
        # Still running, update progress
        wm.progress_update(int(_generation_state.progress * 100))
        return 0.1  # Continue polling every 100ms


class A2F_OT_generate(bpy.types.Operator):
    """Generate facial animation from audio using Audio2Face-3D"""
    bl_idname = "a2f.generate"
    bl_label = "Generate Facial Animation"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return not props.is_generating

    def execute(self, context):
        global _generation_state, _generation_thread

        props = _get_props(context)
        prefs = _get_prefs()

        # ── Validate inputs ──
        if not props.audio_file:
            self.report({'ERROR'}, "No audio file selected. Please choose a WAV file.")
            return {'CANCELLED'}

        if not props.target_mesh:
            self.report({'ERROR'}, "No target mesh selected. Please select a mesh object.")
            return {'CANCELLED'}

        mesh_obj = props.target_mesh
        if not mesh_obj.data.shape_keys:
            if prefs.auto_create_shapekeys:
                # Auto-create shape keys
                mesh_obj.shape_key_add(name="Basis")
                for name in constants.ARKIT_BLENDSHAPE_NAMES:
                    mesh_obj.shape_key_add(name=name)
                self.report({'INFO'}, f"Created {len(constants.ARKIT_BLENDSHAPE_NAMES)} ARKit shape keys.")
            else:
                self.report({'ERROR'}, "Target mesh has no shape keys. Enable auto-create or click 'Create Shape Keys'.")
                return {'CANCELLED'}

        mode = props.connection_mode
        api_key = prefs.api_key
        if mode == "CLOUD" and not api_key:
            self.report({'ERROR'}, "No API key configured. Get one free at build.nvidia.com")
            return {'CANCELLED'}

        # ── Process audio ──
        try:
            audio_chunks, sample_rate, info_msgs = audio.process_audio(
                bpy.path.abspath(props.audio_file)
            )
        except audio.AudioError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        for msg in info_msgs:
            self.report({'INFO'}, msg)

        # ── Build config ──
        function_id = constants.MODEL_FUNCTION_IDS.get(props.model, "")
        face_params = _build_face_params(props)
        emotion_params = _build_emotion_params(props)
        manual_emotions = _build_manual_emotions(props)

        # Auto-map if needed
        if not props.mapping_items:
            mapping_dict = mapping.auto_map(mesh_obj, props.mapping_preset)
            props.mapping_items.clear()
            for arkit_name in constants.ARKIT_BLENDSHAPE_NAMES:
                item = props.mapping_items.add()
                item.arkit_name = arkit_name
                item.blender_name = mapping_dict.get(arkit_name, "")
                item.enabled = True
                item.multiplier = 1.0

        # ── Start generation ──
        _generation_state = client.GenerationState()
        props.is_generating = True
        props.generation_progress = 0.0
        props.last_status = "Generating..."

        context.window_manager.progress_begin(0, 100)

        _generation_thread = threading.Thread(
            target=_run_generation,
            args=(
                mode,
                api_key,
                function_id,
                props.server_url,
                audio_chunks,
                sample_rate,
                face_params,
                emotion_params,
                constants.DEFAULT_WEIGHT_MULTIPLIERS.copy(),
                constants.DEFAULT_WEIGHT_OFFSETS.copy(),
                manual_emotions,
                _generation_state,
            ),
            daemon=True,
        )
        _generation_thread.start()

        bpy.app.timers.register(_poll_generation, first_interval=0.1)

        return {'FINISHED'}


class A2F_OT_test_connection(bpy.types.Operator):
    """Test connection to Audio2Face-3D service"""
    bl_idname = "a2f.test_connection"
    bl_label = "Test Connection"

    _state: dict = {}

    @classmethod
    def poll(cls, context):
        return not context.scene.a2f_props.is_generating

    def execute(self, context):
        props = _get_props(context)
        prefs = _get_prefs()

        mode = props.connection_mode
        result = {"done": False, "success": False, "message": ""}

        def _run_check():
            async def _check():
                if mode == "CLOUD":
                    api_key = prefs.api_key
                    function_id = constants.MODEL_FUNCTION_IDS.get(props.model, "")
                    if not api_key:
                        result["done"] = True
                        result["message"] = "No API key configured."
                        return
                    channel = client.create_cloud_channel(api_key, function_id)
                else:
                    channel = client.create_local_channel(props.server_url)

                try:
                    success, message = await client.health_check(channel)
                    result["success"] = success
                    result["message"] = message
                finally:
                    await channel.close()
                    result["done"] = True

            asyncio.run(_check())

        thread = threading.Thread(target=_run_check, daemon=True)
        thread.start()
        thread.join(timeout=10)

        if result["done"]:
            level = 'INFO' if result["success"] else 'ERROR'
            self.report({level}, result["message"])
            props.last_status = result["message"]
        else:
            self.report({'ERROR'}, "Connection test timed out.")
            props.last_status = "Connection timed out"

        return {'FINISHED'}


class A2F_OT_setup_shapekeys(bpy.types.Operator):
    """Create all 52 ARKit shape keys on target mesh"""
    bl_idname = "a2f.setup_shapekeys"
    bl_label = "Create ARKit Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return props.target_mesh is not None and props.target_mesh.type == 'MESH'

    def execute(self, context):
        props = _get_props(context)
        mesh_obj = props.target_mesh

        if not mesh_obj.data.shape_keys:
            mesh_obj.shape_key_add(name="Basis")

        existing = {kb.name for kb in mesh_obj.data.shape_keys.key_blocks}
        created = 0

        for name in constants.ARKIT_BLENDSHAPE_NAMES:
            if name not in existing:
                mesh_obj.shape_key_add(name=name)
                created += 1

        already = len(constants.ARKIT_BLENDSHAPE_NAMES) - created
        self.report({'INFO'}, f"Created {created} new shape keys ({already} already existed)")
        return {'FINISHED'}


class A2F_OT_auto_map(bpy.types.Operator):
    """Auto-map shape keys using selected preset"""
    bl_idname = "a2f.auto_map"
    bl_label = "Auto-Map Shape Keys"

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return (
            props.target_mesh is not None
            and props.target_mesh.data.shape_keys is not None
        )

    def execute(self, context):
        props = _get_props(context)
        mesh_obj = props.target_mesh

        mapping_dict = mapping.auto_map(mesh_obj, props.mapping_preset)

        # Update mapping_items collection
        props.mapping_items.clear()
        for arkit_name in constants.ARKIT_BLENDSHAPE_NAMES:
            item = props.mapping_items.add()
            item.arkit_name = arkit_name
            item.blender_name = mapping_dict.get(arkit_name, "")
            item.enabled = True
            item.multiplier = 1.0

        mapped, total = mapping.count_mapped(mapping_dict)
        self.report({'INFO'}, f"Mapped {mapped}/{total} shape keys. {total - mapped} unmapped.")
        return {'FINISHED'}


class A2F_OT_clear_animation(bpy.types.Operator):
    """Clear all Audio2Face animation from target mesh"""
    bl_idname = "a2f.clear_animation"
    bl_label = "Clear A2F Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return props.target_mesh is not None

    def execute(self, context):
        props = _get_props(context)
        mapping_dict = _build_mapping(props)

        cleared = animation.clear_animation(props.target_mesh, mapping_dict)
        self.report({'INFO'}, f"Cleared animation from {cleared} shape keys.")
        props.last_status = f"Cleared {cleared} shape keys"
        return {'FINISHED'}


class A2F_OT_reset_face_params(bpy.types.Operator):
    """Reset face parameters to defaults"""
    bl_idname = "a2f.reset_face_params"
    bl_label = "Reset to Defaults"

    def execute(self, context):
        props = _get_props(context)
        defaults = constants.DEFAULT_FACE_PARAMS
        props.skin_strength = defaults["skinStrength"]
        props.upper_face_strength = defaults["upperFaceStrength"]
        props.upper_face_smoothing = defaults["upperFaceSmoothing"]
        props.lower_face_strength = defaults["lowerFaceStrength"]
        props.lower_face_smoothing = defaults["lowerFaceSmoothing"]
        props.face_mask_level = defaults["faceMaskLevel"]
        props.face_mask_softness = defaults["faceMaskSoftness"]
        props.eyelid_open_offset = defaults["eyelidOpenOffset"]
        props.lip_open_offset = defaults["lipOpenOffset"]
        self.report({'INFO'}, "Face parameters reset to defaults.")
        return {'FINISHED'}


class A2F_OT_export_csv(bpy.types.Operator, ExportHelper):
    """Export animation data to CSV (NVIDIA format)"""
    bl_idname = "a2f.export_csv"
    bl_label = "Export Animation CSV"

    filename_ext = ".csv"
    filter_glob: StringProperty(default="*.csv", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return props.last_frame_count > 0

    def execute(self, context):
        props = _get_props(context)
        mesh_obj = props.target_mesh

        if not mesh_obj or not mesh_obj.data.shape_keys:
            self.report({'ERROR'}, "No mesh with shape keys to export.")
            return {'CANCELLED'}

        mapping_dict = _build_mapping(props)
        action = mesh_obj.data.shape_keys.animation_data.action if mesh_obj.data.shape_keys.animation_data else None

        if not action:
            self.report({'ERROR'}, "No animation data to export.")
            return {'CANCELLED'}

        # Collect frame range
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        scene_fps = context.scene.render.fps

        # Write CSV
        header = ["timeCode"] + [f"blendShapes.{name}" for name in constants.ARKIT_BLENDSHAPE_NAMES]

        with open(self.filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for frame in range(frame_start, frame_end + 1):
                time_code = (frame - frame_start) / scene_fps
                row = [f"{time_code:.6f}"]

                for arkit_name in constants.ARKIT_BLENDSHAPE_NAMES:
                    blender_name = mapping_dict.get(arkit_name, "")
                    value = 0.0
                    if blender_name and blender_name in mesh_obj.data.shape_keys.key_blocks:
                        data_path = f'key_blocks["{blender_name}"].value'
                        fcurve = action.fcurves.find(data_path)
                        if fcurve:
                            value = fcurve.evaluate(frame)
                    row.append(f"{value:.6f}")

                writer.writerow(row)

        num_frames = frame_end - frame_start + 1
        self.report({'INFO'}, f"Exported {num_frames} frames to {self.filepath}")
        return {'FINISHED'}


class A2F_OT_import_csv(bpy.types.Operator, ImportHelper):
    """Import animation data from CSV (NVIDIA format)"""
    bl_idname = "a2f.import_csv"
    bl_label = "Import Animation CSV"

    filename_ext = ".csv"
    filter_glob: StringProperty(default="*.csv", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return props.target_mesh is not None

    def execute(self, context):
        props = _get_props(context)
        mesh_obj = props.target_mesh

        if not mesh_obj:
            self.report({'ERROR'}, "No target mesh selected.")
            return {'CANCELLED'}

        if not mesh_obj.data.shape_keys:
            self.report({'ERROR'}, "Target mesh has no shape keys.")
            return {'CANCELLED'}

        # Parse CSV
        frames = []
        try:
            with open(self.filepath, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    time_code = float(row.get("timeCode", 0.0))
                    weights = {}
                    for col_name, value in row.items():
                        if col_name.startswith("blendShapes."):
                            arkit_name = col_name.replace("blendShapes.", "")
                            weights[arkit_name] = float(value)
                    if weights:
                        frames.append(client.AnimationFrame(
                            time_code=time_code,
                            weights=weights,
                        ))
        except Exception as e:
            self.report({'ERROR'}, f"Failed to parse CSV: {e}")
            return {'CANCELLED'}

        if not frames:
            self.report({'ERROR'}, "No animation data found in CSV.")
            return {'CANCELLED'}

        # Apply
        mapping_dict = _build_mapping(props)
        num_keyframes = animation.apply_animation(
            mesh_obj=mesh_obj,
            frames=frames,
            mapping=mapping_dict,
            scene_fps=context.scene.render.fps,
            frame_offset=props.frame_start,
        )

        self.report({'INFO'}, f"Imported {len(frames)} frames ({num_keyframes} keyframes).")
        props.last_status = f"Imported {len(frames)} frames"
        props.last_frame_count = len(frames)
        return {'FINISHED'}


_classes = (
    A2F_OT_generate,
    A2F_OT_test_connection,
    A2F_OT_setup_shapekeys,
    A2F_OT_auto_map,
    A2F_OT_clear_animation,
    A2F_OT_reset_face_params,
    A2F_OT_export_csv,
    A2F_OT_import_csv,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/operators.py
git commit -m "feat: add all operators — generate, test, setup, map, clear, CSV import/export"
```

---

## Task 12: Implement All UI Panels

**Files:**
- Modify: `nvidia_audio2face/panels.py`

**Step 1: Write panels.py with all panels**

```python
"""UI panels for Audio2Face addon in 3D Viewport sidebar."""
import bpy

from . import constants
from .core.mapping import count_mapped


class A2F_PT_main(bpy.types.Panel):
    """Main Audio2Face panel"""
    bl_label = "Audio2Face"
    bl_idname = "A2F_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        # Audio file
        layout.prop(props, "audio_file")

        # Target mesh
        layout.prop(props, "target_mesh")

        # Model
        layout.prop(props, "model")

        # Frame start
        layout.prop(props, "frame_start")

        layout.separator()

        # Generate button
        row = layout.row(align=True)
        row.scale_y = 1.5
        if props.is_generating:
            row.enabled = False
            pct = int(props.generation_progress * 100)
            row.operator("a2f.generate", text=f"Generating... {pct}%", icon='SORTTIME')
        else:
            row.operator("a2f.generate", text="Generate Animation", icon='PLAY')

        # Status
        if props.last_status:
            box = layout.box()
            if "Error" in props.last_status:
                box.alert = True
            box.label(text=props.last_status, icon='INFO')

        layout.separator()

        # Action buttons row
        row = layout.row(align=True)
        row.operator("a2f.clear_animation", text="Clear", icon='TRASH')
        row.operator("a2f.export_csv", text="Export CSV", icon='EXPORT')
        row.operator("a2f.import_csv", text="Import CSV", icon='IMPORT')


class A2F_PT_emotion(bpy.types.Panel):
    """Emotion controls sub-panel"""
    bl_label = "Emotion Controls"
    bl_idname = "A2F_PT_emotion"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        layout.prop(props, "auto_emotion")

        layout.separator()

        layout.prop(props, "emotion_strength")
        layout.prop(props, "emotion_contrast")
        layout.prop(props, "max_emotions")

        if not props.auto_emotion:
            layout.separator()
            layout.label(text="Manual Emotion Override:")

            col = layout.column(align=True)
            col.prop(props, "emotion_joy")
            col.prop(props, "emotion_anger")
            col.prop(props, "emotion_sadness")
            col.prop(props, "emotion_fear")
            col.prop(props, "emotion_amazement")
            col.prop(props, "emotion_disgust")
            col.prop(props, "emotion_cheekiness")
            col.prop(props, "emotion_grief")
            col.prop(props, "emotion_pain")
            col.prop(props, "emotion_outofbreath")


class A2F_PT_face_params(bpy.types.Panel):
    """Face parameters sub-panel"""
    bl_label = "Face Parameters"
    bl_idname = "A2F_PT_face_params"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        col = layout.column(align=True)
        col.prop(props, "skin_strength")
        col.prop(props, "upper_face_strength")
        col.prop(props, "upper_face_smoothing")
        col.prop(props, "lower_face_strength")
        col.prop(props, "lower_face_smoothing")
        col.prop(props, "face_mask_level")
        col.prop(props, "face_mask_softness")
        col.prop(props, "eyelid_open_offset")
        col.prop(props, "lip_open_offset")

        layout.separator()
        layout.operator("a2f.reset_face_params", icon='LOOP_BACK')


class A2F_PT_mapping(bpy.types.Panel):
    """Shape key mapping sub-panel"""
    bl_label = "Shape Key Mapping"
    bl_idname = "A2F_PT_mapping"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        layout.prop(props, "mapping_preset")

        row = layout.row(align=True)
        row.operator("a2f.auto_map", text="Auto-Map", icon='FILE_REFRESH')
        row.operator("a2f.setup_shapekeys", text="Create Missing", icon='ADD')

        # Show mapping status
        if props.mapping_items:
            mapping_dict = {
                item.arkit_name: item.blender_name
                for item in props.mapping_items
            }
            mapped, total = count_mapped(mapping_dict)
            layout.label(text=f"Status: {mapped}/{total} mapped")

            # Show mapping list (scrollable)
            box = layout.box()
            col = box.column(align=True)
            for item in props.mapping_items:
                row = col.row(align=True)
                row.prop(item, "enabled", text="")

                sub = row.split(factor=0.45, align=True)
                sub.label(text=item.arkit_name)

                if item.blender_name:
                    sub.label(text=item.blender_name)
                else:
                    sub.alert = True
                    sub.label(text="(unmapped)")

                row.prop(item, "multiplier", text="", slider=True)


class A2F_PT_settings(bpy.types.Panel):
    """Connection settings sub-panel"""
    bl_label = "Connection Settings"
    bl_idname = "A2F_PT_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props
        prefs = context.preferences.addons[__package__].preferences

        layout.prop(props, "connection_mode", expand=True)

        layout.separator()

        if props.connection_mode == 'CLOUD':
            layout.prop(prefs, "api_key")
            layout.label(text="Get a free key at build.nvidia.com", icon='URL')
        else:
            layout.prop(props, "server_url")

        layout.separator()
        layout.operator("a2f.test_connection", icon='LINKED')


_classes = (
    A2F_PT_main,
    A2F_PT_emotion,
    A2F_PT_face_params,
    A2F_PT_mapping,
    A2F_PT_settings,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
```

**Step 2: Commit**

```bash
git add nvidia_audio2face/panels.py
git commit -m "feat: add all UI panels — main, emotion, face params, mapping, settings"
```

---

## Task 13: Update __init__.py Module Loading Order

**Files:**
- Modify: `nvidia_audio2face/__init__.py`

**Step 1: Verify __init__.py loads modules in correct order**

The order should be: constants → properties → preferences → operators → panels.

This was already set up in Task 1. Verify it's correct and that `vendor/` path is added to `sys.path` before any module that imports `nvidia_ace`.

**Step 2: Add reload support for development**

Update `__init__.py` to support Blender's F8 reload:

```python
# At the top of __init__.py, after bl_info:

import importlib
import sys
import os

_vendor_path = os.path.join(os.path.dirname(__file__), "vendor")
if _vendor_path not in sys.path:
    sys.path.insert(0, _vendor_path)

# Support reload (F8 in Blender)
if "constants" in locals():
    importlib.reload(constants)
    importlib.reload(properties)
    importlib.reload(preferences)
    importlib.reload(operators)
    importlib.reload(panels)

from . import constants
from . import properties
from . import preferences
from . import operators
from . import panels

# ... rest of register/unregister
```

**Step 3: Commit**

```bash
git add nvidia_audio2face/__init__.py
git commit -m "feat: add reload support and correct module loading order"
```

---

## Task 14: Create License Files

**Files:**
- Create: `nvidia_audio2face/LICENSES/MIT-nvidia-ace.txt`
- Create: `nvidia_audio2face/LICENSES/Apache-2.0-grpcio.txt`
- Create: `nvidia_audio2face/LICENSES/BSD-3-protobuf.txt`
- Create: `nvidia_audio2face/LICENSE.txt`

**Step 1: Create LICENSES directory**

```bash
mkdir -p nvidia_audio2face/LICENSES
```

**Step 2: Write license files**

Create each file with the appropriate license text:
- MIT for nvidia_ace stubs (from Maya-ACE)
- Apache 2.0 for grpcio
- BSD-3-Clause for protobuf
- GPL-3.0 for the addon itself (for Blender Extensions distribution)

**Step 3: Commit**

```bash
git add nvidia_audio2face/LICENSES/ nvidia_audio2face/LICENSE.txt
git commit -m "feat: add license files for bundled dependencies"
```

---

## Task 15: Integration Test — Addon Registration

**Step 1: Test addon loads in Blender without errors**

Open Blender and run in the Python console:

```python
import sys
sys.path.insert(0, "/path/to/project")
import nvidia_audio2face
nvidia_audio2face.register()
```

Verify:
- No import errors
- Panel appears in 3D Viewport sidebar under "Audio2Face" tab
- All sub-panels expand/collapse correctly
- Preferences appear under Edit > Preferences > Add-ons
- All operators appear in F3 search (a2f.generate, a2f.test_connection, etc.)

**Step 2: Test addon unregister**

```python
nvidia_audio2face.unregister()
```

Verify: No errors, panel disappears.

**Step 3: Fix any issues found**

Address import errors, missing `__init__.py` files, protobuf stub path issues, etc.

**Step 4: Commit fixes**

```bash
git add -A
git commit -m "fix: resolve integration issues from addon registration testing"
```

---

## Task 16: Integration Test — Full Generation Pipeline

**Step 1: Prepare test audio**

Create or obtain a short WAV file (3-5 seconds, 16-bit PCM, mono, 16kHz).

**Step 2: Test full pipeline in Blender**

1. Enable addon in Blender preferences
2. Enter API key in preferences
3. Create a cube mesh in scene
4. In Audio2Face panel:
   - Select the WAV file
   - Select the cube as target mesh
   - Click "Create Missing" to add shape keys
   - Click "Auto-Map"
   - Click "Generate Animation"
5. Verify:
   - Progress bar appears and updates
   - Status changes from "Generating..." to "Generated N frames"
   - Shape keys have keyframes on timeline
   - Timeline scrubbing shows shape key value changes

**Step 3: Test error cases**

- No audio file → error message
- No mesh → error message
- Wrong API key → error message
- Non-WAV file → error message

**Step 4: Test CSV export/import**

1. After generation, click "Export CSV"
2. Verify CSV file matches NVIDIA format
3. Clear animation, then "Import CSV" with the exported file
4. Verify keyframes are restored

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve issues from full pipeline integration testing"
```

---

## Task 17: Polish — Edge Case Handling

**Files:**
- Modify: `nvidia_audio2face/operators.py`

**Step 1: Add generation cancellation safety**

In `_poll_generation()`, check if the target mesh still exists:

```python
# In _poll_generation, before applying animation:
if not props.target_mesh or props.target_mesh.name not in bpy.data.objects:
    props.last_status = "Error: Target mesh was deleted during generation"
    props.is_generating = False
    wm.progress_end()
    _generation_state = None
    return None
```

**Step 2: Add unregister cleanup**

In `operators.py` unregister function, cancel any running generation:

```python
def unregister():
    global _generation_state, _generation_thread
    _generation_state = None
    _generation_thread = None
    # ... unregister classes
```

**Step 3: Commit**

```bash
git add nvidia_audio2face/operators.py
git commit -m "fix: add edge case handling — mesh deletion, addon unregister cleanup"
```

---

## Task 18: Write README with Quick Start Guide

**Files:**
- Modify: `README.md`

**Step 1: Write comprehensive README**

Include:
1. One-line description
2. Screenshot placeholder
3. Features list
4. Quick Start (5 steps): Install → Get API Key → Select Audio → Select Mesh → Generate
5. Getting NVIDIA API key walkthrough
6. Supported audio formats
7. Connection modes (Cloud vs Local)
8. Shape key mapping guide
9. CSV import/export
10. Troubleshooting FAQ
11. License info

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with quick start and troubleshooting"
```

---

## Task 19: Final Verification and Release Commit

**Step 1: Verify complete file structure**

```
nvidia_audio2face/
├── __init__.py
├── blender_manifest.toml
├── LICENSE.txt
├── constants.py
├── properties.py
├── preferences.py
├── operators.py
├── panels.py
├── core/
│   ├── __init__.py
│   ├── client.py
│   ├── audio.py
│   ├── mapping.py
│   └── animation.py
├── vendor/
│   └── nvidia_ace/
│       ├── __init__.py
│       ├── a2f/v1_pb2.py
│       ├── audio/v1_pb2.py
│       ├── controller/v1_pb2.py
│       ├── animation_data/v1_pb2.py
│       ├── emotion_with_timecode/v1_pb2.py
│       ├── status/v1_pb2.py
│       └── services/a2f_controller/v1_pb2_grpc.py
├── wheels/
│   ├── grpcio-*.whl (3 platforms)
│   └── protobuf-*.whl (3 platforms)
└── LICENSES/
    ├── MIT-nvidia-ace.txt
    ├── Apache-2.0-grpcio.txt
    └── BSD-3-protobuf.txt
```

**Step 2: Test clean install**

1. ZIP the `nvidia_audio2face/` directory
2. Install in Blender via Edit > Preferences > Add-ons > Install
3. Enable, verify it loads
4. Run a generation test

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Audio2Face for Blender v1.0.0 — complete addon ready for release"
```

---

## Summary: Task Dependency Graph

```
Task  1: Skeleton ──────┐
Task  2: Constants ──────┤
Task  3: Proto Stubs ────┤
Task  4: Wheels ─────────┤
Task  5: Preferences ────┼──→ Task 11: Operators ──→ Task 15: Registration Test
Task  6: Properties ─────┤                      └──→ Task 16: Pipeline Test
Task  7: Audio Module ───┤                           └──→ Task 17: Edge Cases
Task  8: gRPC Client ────┤
Task  9: Mapping Module ─┤
Task 10: Animation ──────┘
                              Task 12: Panels ──────→ Task 15
                              Task 13: Init Update ──→ Task 15
                              Task 14: Licenses ─────→ Task 19
                              Task 18: README ────────→ Task 19
```

**Tasks 1-10** can be done in any order (they're independent modules).
**Tasks 11-12** depend on 1-10 (they import from all modules).
**Task 13** depends on 1-12 (wires everything together).
**Tasks 15-16** are integration tests (depend on 13).
**Task 17** is polish (depends on 16).
**Tasks 18-19** are documentation and release (depend on 17).

---

## Estimated Scope

- **19 tasks** total
- **~15 files** to create
- **~2,500 lines of code** (Python)
- **Tasks 1-14**: Can be parallelized heavily (independent modules)
- **Tasks 15-19**: Sequential (integration, testing, polish)
