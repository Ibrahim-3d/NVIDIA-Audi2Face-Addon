# NVIDIA Audio2Face-3D Blender Addon — Master Plan

## Executive Summary

Build a commercial Blender addon that brings NVIDIA's Audio2Face-3D AI-powered facial
animation directly into Blender. The addon converts speech audio into 52 ARKit blendshape
weights at 30 FPS — generating full-face animation (lips, jaw, brows, cheeks, nose, eyes)
with automatic emotion detection. This fills the biggest gap in NVIDIA's Audio2Face-3D
ecosystem: Maya and Unreal Engine have official plugins, **Blender has nothing**.

---

## 1. Technology Overview

### What is Audio2Face-3D?
NVIDIA's open-source (MIT license, Oct 2025) deep learning system that transforms audio
input into highly detailed facial animations. It uses a Transformer + Diffusion architecture
based on HuBERT with ~180M parameters.

### What it outputs
- **52 ARKit blendshape weights** per frame at 30 FPS
- **Emotion data** (amazement, anger, cheekiness, disgust, fear, grief, joy, outofbreath, pain, sadness)
- **Processed audio** (echo-back for sync verification)

### What it does NOT animate
- Eye look-direction (EyeLookDown/In/Out/Up) — always 0
- TongueOut — always 0
- Head rotation / body movement

### Available models
| Model | Best For | Notes |
|-------|----------|-------|
| Audio2Face-3D v3.0 | Best overall quality | Diffusion-based, multiple identities |
| A2F v2.3-James | English male voice, strong emotion | Lower VRAM, regression-based |
| A2F v2.3-Claire | Chinese + English female voice | Lower VRAM |
| A2F v2.3-Mark | English male, high-res geometry | Lower VRAM |
| Audio2Emotion v3.0 | Emotion detection | Experimental |
| Audio2Emotion v2.2 | Emotion detection | Stable |

---

## 2. Integration Architecture

### Connection Modes (priority order)

#### Mode 1: NVIDIA Cloud API (Default — Zero Friction)
- Endpoint: `grpc.nvcf.nvidia.com:443`
- Auth: `Bearer <API_KEY>` + `function-id` header metadata
- Channel: `grpc.aio.secure_channel` with SSL + composite credentials
- Free tier: 1,000+ credits at build.nvidia.com
- No local GPU required, no Docker, no SDK build

#### Mode 2: Local NIM Server (Studios)
- Endpoint: `localhost:52000` (configurable)
- Channel: `grpc.aio.insecure_channel` (or TLS/mTLS)
- Requires: Docker + NVIDIA GPU on server
- Deploy via: `docker-compose.yml` from Audio2Face-3D-Samples

#### Mode 3: Local C++ SDK (Stretch Goal — Fully Offline)
- Library: `libaudio2x.so` / `audio2x.dll`
- Interface: ctypes wrapper around C API
- Requires: NVIDIA GPU + CUDA + TensorRT + model files from HuggingFace
- Models stored locally, no network needed

### gRPC Protocol (Exact Specification)

**Service**: `nvidia_ace.services.a2f_controller.v1.A2FControllerService`
**Method**: `ProcessAudioStream` (bidirectional streaming)

#### SEND sequence (client → server):
```
Message 1: AudioStream(
  audio_stream_header=AudioStreamHeader(
    audio_header=AudioHeader(
      samples_per_second=16000,
      bits_per_sample=16,
      channel_count=1,
      audio_format=AUDIO_FORMAT_PCM
    ),
    emotion_post_processing_params=EmotionPostProcessingParameters(
      emotion_contrast=1.0,
      live_blend_coef=0.7,
      enable_preferred_emotion=False,
      preferred_emotion_strength=0.5,
      emotion_strength=0.6,
      max_emotions=3
    ),
    face_params=FaceParameters(float_params={
      "upperFaceStrength": 1.0,
      "upperFaceSmoothing": 0.001,
      "lowerFaceStrength": 1.2,
      "lowerFaceSmoothing": 0.006,
      "faceMaskLevel": 0.6,
      "faceMaskSoftness": 0.0085,
      "skinStrength": 1.0,
      "eyelidOpenOffset": 0.06,
      "lipOpenOffset": -0.02
    }),
    blendshape_params=BlendShapeParameters(
      bs_weight_multipliers={...52 entries...},
      bs_weight_offsets={...52 entries...},
      enable_clamping_bs_weight=False
    ),
    emotion_params=EmotionParameters(
      live_transition_time=0.0001,
      beginning_emotion={...}
    )
  )
)

Message 2..N: AudioStream(
  audio_with_emotion=AudioWithEmotion(
    audio_buffer=<1 second of PCM16 bytes>,
    emotions=[EmotionWithTimeCode(emotion={...}, time_code=0.0)]  # first chunk only
  )
)

Message N+1: AudioStream(end_of_audio=EndOfAudio())
```

#### RECEIVE sequence (server → client):
```
Message 1: AnimationDataStream(
  animation_data_stream_header=AnimationDataStreamHeader(
    skel_animation_header.blend_shapes=["EyeBlinkLeft", "EyeLookDownLeft", ...],
    audio_header=AudioHeader(...)
  )
)

Message 2..M: AnimationDataStream(
  animation_data=AnimationData(
    skel_animation.blend_shape_weights=[
      {time_code: 0.0, values: [0.0, 0.0, ...]},
      {time_code: 0.033, values: [0.01, 0.0, ...]},
      ...
    ],
    metadata["emotion_aggregate"]=EmotionAggregate(...),
    audio.audio_buffer=<bytes>
  )
)

Message M+1: AnimationDataStream(
  status=Status(code=0, message="SUCCESS")
)
```

#### Status codes:
- 0 = SUCCESS
- 1 = INFO
- 2 = WARNING
- 3 = ERROR

### Protobuf Stubs Source
The Maya-ACE repo (`github.com/NVIDIA/Maya-ACE`) ships pre-compiled Python protobuf
stubs at `python/grpc_py/nvidia_ace/`. These are MIT-licensed and include:

```
nvidia_ace/
├── a2f/v1_pb2.py                           # AudioWithEmotion, FaceParameters, BlendShapeParameters
├── audio/v1_pb2.py                         # AudioHeader
├── controller/v1_pb2.py                    # AudioStream, AudioStreamHeader, AnimationDataStream
├── animation_data/v1_pb2.py                # AnimationData, AnimationDataStreamHeader
├── emotion_with_timecode/v1_pb2.py         # EmotionWithTimeCode
├── emotion_aggregate/v1_pb2.py             # EmotionAggregate
├── status/v1_pb2.py                        # Status
└── services/a2f_controller/v1_pb2_grpc.py  # A2FControllerServiceStub
```

We bundle these directly instead of depending on `nvidia-audio2face-3d` from PyPI.

---

## 3. The 52 ARKit Blendshapes

Ordered exactly as NVIDIA's config files define them:

```
 0  EyeBlinkLeft        26  MouthFrownLeft
 1  EyeLookDownLeft      27  MouthFrownRight
 2  EyeLookInLeft        28  MouthDimpleLeft
 3  EyeLookOutLeft       29  MouthDimpleRight
 4  EyeLookUpLeft        30  MouthStretchLeft
 5  EyeSquintLeft        31  MouthStretchRight
 6  EyeWideLeft          32  MouthRollLower
 7  EyeBlinkRight        33  MouthRollUpper
 8  EyeLookDownRight     34  MouthShrugLower
 9  EyeLookInRight       35  MouthShrugUpper
10  EyeLookOutRight      36  MouthPressLeft
11  EyeLookUpRight       37  MouthPressRight
12  EyeSquintRight       38  MouthLowerDownLeft
13  EyeWideRight         39  MouthLowerDownRight
14  JawForward           40  MouthUpperUpLeft
15  JawLeft              41  MouthUpperUpRight
16  JawRight             42  BrowDownLeft
17  JawOpen              43  BrowDownRight
18  MouthClose           44  BrowInnerUp
19  MouthFunnel          45  BrowOuterUpLeft
20  MouthPucker          46  BrowOuterUpRight
21  MouthLeft            47  CheekPuff
22  MouthRight           48  CheekSquintLeft
23  MouthSmileLeft       49  CheekSquintRight
24  MouthSmileRight      50  NoseSneerLeft
25  MouthFrownLeft       51  NoseSneerRight
                          (52  TongueOut — always 0)
```

Note: `MouthClose` deviates from standard ARKit — it includes jaw opening.

### Default Weight Multipliers (James model)
Zeroed: EyeLookDown/In/Out/Up (both sides), TongueOut
Reduced: JawLeft/Right (0.2), MouthLeft/Right (0.2), MouthStretchLeft/Right (0.05), CheekPuff (0.2)
Boosted: MouthSmileLeft/Right (1.2), BrowDownLeft/Right (1.2), BrowInnerUp (1.3), LowerFaceStrength (1.2)

---

## 4. Blender-Specific Technical Constraints

### Threading Model
- Blender does NOT allow bpy calls from threads — will crash
- gRPC client (asyncio) must run in a background `threading.Thread`
- Results stored in a thread-safe `queue.Queue` or shared list
- `bpy.app.timers.register()` callback polls results every 0.1s
- Timer applies blendshape keyframes on the main thread
- Progress reported via `context.window_manager.progress_begin/update/end`

### Shape Key System
- Shape keys are stored on `mesh.shape_keys.key_blocks`
- `key_blocks[0]` is always "Basis" (reference shape)
- Each ARKit shape = one key_block with `value` 0.0–1.0
- Keyframes inserted via `key_block.keyframe_insert(data_path="value", frame=N)`
- For 52 shapes × 30 FPS × 10s = 15,600 keyframes per clip

### Frame Rate Conversion
- A2F outputs at exactly 30 FPS (timecode 0.0, 0.033, 0.066, ...)
- Blender scene may be 24/25/30/60 FPS
- When scene FPS ≠ 30: interpolate between nearest A2F frames
- Formula: `blender_frame = a2f_timecode * scene_fps + frame_offset`

### Audio Requirements
- Format: WAV, PCM 16-bit
- Channels: Mono (auto-convert stereo by averaging channels)
- Sample rate: 16kHz preferred (auto-resample from any rate)
- Max duration: 300 seconds per clip
- Chunk size: 1 second per gRPC buffer (= samplerate samples per chunk)

### Blender Version Support
- Primary target: Blender 4.2+ (Extension system with `blender_manifest.toml`)
- Include `bl_info` for backwards compatibility with 3.6+
- Use `blender_manifest.toml` `[permissions]` to declare `network` and `files`
- Bundle wheels in `wheels/` directory for dependency management

---

## 5. Addon File Structure

```
nvidia_audio2face/
├── __init__.py                  # bl_info + register/unregister + reload support
├── blender_manifest.toml        # Blender 4.2+ extension manifest
├── constants.py                 # 52 ARKit names, emotions, default multipliers/offsets
├── properties.py                # Scene PropertyGroup (all addon state)
├── preferences.py               # AddonPreferences (API key, server URL, defaults)
├── operators.py                 # All operators (generate, bake, setup, preview, clear, test)
├── panels.py                    # All UI panels (main, emotion, mapping, settings)
├── core/
│   ├── __init__.py
│   ├── client.py                # gRPC client (cloud + local, asyncio in thread)
│   ├── audio.py                 # Load WAV, validate, resample, chunk
│   ├── mapping.py               # ARKit ↔ shape key mapping + presets
│   └── animation.py             # Apply weights to shape keys, bake keyframes, FPS convert
├── vendor/
│   └── nvidia_ace/              # Bundled protobuf stubs from Maya-ACE (MIT licensed)
│       ├── a2f/v1_pb2.py
│       ├── audio/v1_pb2.py
│       ├── controller/v1_pb2.py
│       ├── animation_data/v1_pb2.py
│       ├── emotion_with_timecode/v1_pb2.py
│       ├── emotion_aggregate/v1_pb2.py
│       ├── status/v1_pb2.py
│       └── services/a2f_controller/v1_pb2_grpc.py
└── wheels/                      # Bundled Python wheels
    ├── grpcio-1.64.1-*.whl
    └── protobuf-5.*.whl
```

---

## 6. Competitive Analysis

| Addon | Tech | Animates | Quality | Price | Our Advantage |
|-------|------|----------|---------|-------|---------------|
| Syncnix | Phoneme rules | Lips only | Basic | ~$30 | Full face + AI quality |
| iocgpoly Lip Sync | Vosk ASR | Lips only | Decent | Free | Full face + emotion |
| Rhubarb Lipsync | CLI phonemes | Lips only | Basic | Free | No CLI, full face |
| Faceit | MoCap + ARKit | Full face | Good | ~$40 | No iPhone needed |
| **Ours** | NVIDIA A2F-3D | Full face | AAA | $29–49 | Neural network, emotion |

---

## 7. Commercial Strategy

### Pricing
- **Blender Extensions**: Free basic version (limited to 10s audio, James model only)
- **Superhive / Gumroad**: $29–49 full version (unlimited, all models, emotion controls)

### Revenue Model
- User buys addon once → user gets own NVIDIA API key (free at build.nvidia.com)
- Zero server costs for us — NVIDIA bears compute
- No subscriptions, no recurring costs for users (beyond API credits)

### NVIDIA Partnership Path
1. Build quality addon → post on NVIDIA Audio2Face Discord
2. Join NVIDIA Developer Program (free) + NVIDIA Connect (free ISV program)
3. Request listing on Audio2Face-3D hub repo + developer.nvidia.com/ace page
4. Apply for NVIDIA Inception if incorporating as startup
5. Submit GTC session proposal

---

## 8. Key References

### NVIDIA Repositories
- Hub: https://github.com/NVIDIA/Audio2Face-3D
- SDK: https://github.com/NVIDIA/Audio2Face-3D-SDK
- Samples: https://github.com/NVIDIA/Audio2Face-3D-Samples
- Maya Plugin: https://github.com/NVIDIA/Maya-ACE
- Training: https://github.com/NVIDIA/Audio2Face-3D-Training-Framework
- Models: https://huggingface.co/nvidia/Audio2Face-3D-v3.0

### NVIDIA Documentation
- Microservice docs: https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/
- ACE page: https://developer.nvidia.com/ace
- NIM API: https://build.nvidia.com/nvidia/audio2face-3d

### Blender Documentation
- Python API: https://docs.blender.org/api/current/
- Extension system: https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html
