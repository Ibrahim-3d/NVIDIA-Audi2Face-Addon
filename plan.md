# NVIDIA Audio2Face-3D Blender Addon — Implementation Plan

## Research Summary

### What is Audio2Face-3D?
NVIDIA's open-source (MIT license, Oct 2025) AI system that generates realistic facial
animations from audio input. It outputs **52 ARKit blendshape weights at 30 FPS** by
analyzing speech phonemes, intonation, and emotion.

### Two Integration Paths Available

| Path | Technology | Pros | Cons |
|------|-----------|------|------|
| **NIM Microservice** | gRPC via `nvidia-audio2face-3d` PyPI pkg | Pure Python, easy setup, streaming | Requires Docker + NVIDIA GPU server |
| **Local C++ SDK** | `libaudio2x.so` / `audio2x.dll` via ctypes | No server needed, offline, fast | Needs SDK build, ctypes wrapper, GPU |

### ARKit Blendshapes Output (52 shapes)
The model outputs standard ARKit blendshape weights including mouth (MouthOpen, MouthSmile,
MouthFunnel, etc.), jaw (JawOpen, JawForward, etc.), brow (BrowDownLeft, BrowInnerUp, etc.),
cheek, nose, and eye regions. Note: eye look-direction and TongueOut are always 0.

---

## Addon Architecture

### Target: Blender 4.2+ (Extension system) with legacy bl_info fallback

```
nvidia_audio2face/
├── __init__.py                  # Registration, bl_info + reload support
├── blender_manifest.toml        # Blender 4.2+ extension manifest
├── preferences.py               # Addon preferences (server URL, SDK path, API key)
├── properties.py                # Scene/object property groups
├── constants.py                 # ARKit blendshape names, defaults
│
├── operators/
│   ├── __init__.py
│   ├── generate.py              # Main operator: audio → blendshapes
│   ├── bake.py                  # Bake animation to keyframes
│   ├── preview.py               # Real-time preview (modal operator)
│   ├── setup_mesh.py            # Create/map ARKit shape keys on mesh
│   └── import_export.py         # Import/export animation CSV/JSON
│
├── panels/
│   ├── __init__.py
│   ├── main_panel.py            # Main N-panel UI
│   ├── settings_panel.py        # Connection & model settings sub-panel
│   └── mapping_panel.py         # Blendshape ↔ shape key mapping sub-panel
│
├── core/
│   ├── __init__.py
│   ├── backend_base.py          # Abstract backend interface
│   ├── backend_grpc.py          # NIM gRPC microservice backend
│   ├── backend_sdk.py           # Local C++ SDK backend (ctypes)
│   ├── audio_utils.py           # Audio loading, resampling to 16kHz
│   ├── blendshape_mapping.py    # ARKit name ↔ Blender shape key mapping
│   └── animation.py             # Apply weights to shape keys / bake keyframes
│
└── wheels/                      # Bundled Python wheels (for extension packaging)
    └── (nvidia-audio2face-3d, grpcio, etc.)
```

---

## Implementation Steps

### Phase 1: Foundation & Project Setup
1. Create the addon package structure with `__init__.py` and `blender_manifest.toml`
2. Implement `constants.py` with the 52 ARKit blendshape names and defaults
3. Implement `properties.py` — scene property group with:
   - Audio file path (StringProperty, FILE_PATH)
   - Target mesh (PointerProperty to Object)
   - Backend selection (EnumProperty: 'GRPC' / 'LOCAL_SDK')
   - Server URL (StringProperty, default `localhost:52000`)
   - Model selection (EnumProperty: 'james_v2.3', 'claire_v2.3', 'mark_v2.3')
   - Emotion parameters (FloatProperties for emotion intensity)
   - Generation status flags
4. Implement `preferences.py` — addon preferences:
   - Default server URL
   - SDK library path
   - NVIDIA API key (for cloud NIM)
   - Auto-create shape keys toggle

### Phase 2: Core Backend — gRPC (NIM Microservice)
5. Implement `core/backend_base.py` — abstract interface:
   - `generate(audio_data, sample_rate, config) → List[BlendshapeFrame]`
   - `health_check() → bool`
   - `get_available_models() → List[str]`
6. Implement `core/backend_grpc.py`:
   - Connect to NIM microservice via gRPC (using `nvidia-audio2face-3d` proto stubs)
   - Stream audio chunks (max 10s per buffer, 300s total)
   - Receive `AnimationDataStream` with blendshape weights per frame
   - Parse `SkelAnimationHeader` for blendshape names
   - Collect per-frame blendshape values at 30 FPS
7. Implement `core/audio_utils.py`:
   - Load WAV/MP3/OGG via Python wave/soundfile
   - Resample to 16kHz (required by A2F)
   - Convert to mono if stereo
   - Chunk audio for streaming (10s max per chunk)

### Phase 3: Mesh Setup & Blendshape Mapping
8. Implement `core/blendshape_mapping.py`:
   - Map ARKit blendshape names to Blender shape key names
   - Support exact match and fuzzy/alias matching
   - Auto-detect existing shape keys on a mesh
   - Report which shapes are mapped vs missing
9. Implement `operators/setup_mesh.py`:
   - Operator to create all 52 ARKit shape keys on selected mesh
   - Operator to auto-map existing shape keys to ARKit names
   - Support custom mapping overrides via UI list

### Phase 4: Animation Generation & Baking
10. Implement `core/animation.py`:
    - Apply a list of `BlendshapeFrame` to mesh shape keys at correct frame timing
    - Convert 30 FPS A2F output to scene frame rate
    - Insert keyframes per shape key per frame
    - Support frame offset for placing animation at arbitrary timeline position
11. Implement `operators/generate.py`:
    - Main operator: load audio → send to backend → receive frames → apply to mesh
    - Run backend call in thread, poll results via timer (Blender threading safety)
    - Progress reporting via window_manager progress bar
    - Error handling with user-facing reports
12. Implement `operators/bake.py`:
    - Bake generated animation data to keyframes
    - Options: frame range, FPS override, selected shapes only
    - Clean up existing keyframes option

### Phase 5: UI Panels
13. Implement `panels/main_panel.py` — N-Panel "Audio2Face" tab:
    - Audio file selector
    - Target mesh selector (eyedropper)
    - Generate button (with progress)
    - Bake to keyframes button
    - Quick status display
14. Implement `panels/settings_panel.py` — sub-panel:
    - Backend selection (gRPC / Local SDK)
    - Server URL / connection test button
    - Model selection dropdown
    - Emotion controls (intensity sliders)
    - FPS / timing settings
15. Implement `panels/mapping_panel.py` — sub-panel:
    - List of ARKit shapes with mapped Blender shape key names
    - Auto-map button
    - Create missing shape keys button
    - Per-shape weight multiplier overrides

### Phase 6: Real-time Preview
16. Implement `operators/preview.py`:
    - Modal operator that plays audio and applies blendshape weights in real-time
    - Uses `bpy.app.timers` or timer-based modal for frame updates
    - Scrub through generated animation
    - Stop/pause controls

### Phase 7: Import/Export
17. Implement `operators/import_export.py`:
    - Export animation as CSV (matching A2F output format: `animation_frames.csv`)
    - Export as JSON (per-frame blendshape dictionary)
    - Import CSV/JSON animation data
    - Import from A2F NIM output files directly

### Phase 8: Local SDK Backend (stretch goal)
18. Implement `core/backend_sdk.py`:
    - ctypes wrapper around `libaudio2x.so` / `audio2x.dll`
    - Load models from Hugging Face cache or local path
    - TensorRT engine conversion support
    - Local inference without network

### Phase 9: Polish & Packaging
19. Bundle required Python wheels for Blender extension packaging
20. Write user documentation / README
21. Handle edge cases: no GPU, network errors, missing shape keys, empty audio
22. Add logging with configurable verbosity

---

## Key Technical Decisions

### Threading Strategy (Critical for Blender)
- Blender does NOT allow `bpy` calls from threads
- Backend inference runs in a Python `threading.Thread`
- Results are communicated back via a shared data structure
- A `bpy.app.timers` callback polls for results and applies them on the main thread
- Progress is updated via `WindowManager.progress_update()`

### Audio Requirements
- 16kHz sample rate (model requirement)
- Mono channel
- Max 300 seconds per clip
- Max 10 seconds per gRPC buffer chunk

### Frame Rate Handling
- A2F outputs at 30 FPS
- Blender scene may be 24/25/30/60 FPS
- Need frame rate conversion when baking keyframes
- Use linear interpolation between A2F frames when scene FPS differs

### Dependencies
- `grpcio` + `protobuf` — for gRPC communication
- `nvidia-audio2face-3d` — proto stubs for A2F NIM
- `numpy` — audio processing and array manipulation
- `soundfile` or `wave` — audio file loading
- `scipy` (optional) — for resampling if soundfile unavailable

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| NIM requires Docker + NVIDIA GPU server | Support NVIDIA Build cloud API as alternative |
| Large wheel dependencies for extension | Use minimal deps, lazy imports |
| Blender Python version mismatch with wheels | Pin compatible versions in manifest |
| No official Python SDK wrapper | Start with gRPC, add ctypes SDK later |
| Shape key mapping varies per character | Flexible mapping UI with presets |
