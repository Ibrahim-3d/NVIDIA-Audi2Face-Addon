# NVIDIA Audio2Face-3D Blender Addon — Commercial Product Plan

## Why This Addon Has a Market

### Competitive Landscape
| Existing Addon | Tech | Quality | Price |
|---------------|------|---------|-------|
| Syncnix | Phoneme mapping | Basic lip-only | Paid (~$20-40) |
| iocgpoly Lip Sync | Vosk speech recognition | Decent lip-only | Free |
| Rhubarb Lipsync | CLI phoneme tool | Basic lip-only | Free |
| Parrot Lipsync | Phoneme JSON tables | Basic lip-only | Free |

### Our Advantage: NVIDIA Audio2Face-3D
- **Neural network** vs rule-based phoneme mapping — far superior quality
- **Full face animation**: brows, cheeks, squints, nose, jaw — not just lips
- **Emotion detection**: automatically detects and expresses emotion from speech
- **52 ARKit blendshapes** at 30 FPS — industry standard, compatible with everything
- **Available models**: James, Claire, Mark — different animation styles

### Target Customer
Blender artists and small studios who want AAA-quality facial animation
without learning complex pipelines. People currently paying for Syncnix
or struggling with Rhubarb's mediocre output.

---

## Product Architecture (Ship-First Approach)

### Core Principle: NVIDIA Cloud API as Primary Backend
Users get a **free** NVIDIA API key at build.nvidia.com (1,000+ credits).
They paste it into addon preferences. That's it — zero infrastructure.

The gRPC call goes to `grpc.nvcf.nvidia.com:443` (NVIDIA's hosted endpoint).
No Docker. No local GPU requirement. No SDK builds.

### Connection Modes (in priority order)
1. **NVIDIA Cloud API** (default) — just an API key, works everywhere
2. **Local NIM Server** — for studios running their own Docker container
3. **Local C++ SDK** — stretch goal for fully offline use

### Minimal File Structure (v1.0 — ship fast)
```
nvidia_audio2face/
├── __init__.py               # bl_info + register/unregister
├── blender_manifest.toml     # Blender 4.2+ extension metadata
├── constants.py              # 52 ARKit blendshape names, emotion names, defaults
├── properties.py             # All scene + object property groups
├── preferences.py            # Addon prefs: API key, server URL, defaults
├── operators.py              # All operators in one file (generate, bake, setup, preview)
├── panels.py                 # All UI panels in one file
├── core/
│   ├── __init__.py
│   ├── client.py             # gRPC client (cloud + local server)
│   ├── audio.py              # Audio loading, validation, resampling
│   ├── mapping.py            # ARKit ↔ shape key mapping + presets
│   └── animation.py          # Apply blendshape weights, bake keyframes
└── wheels/                   # Bundled: grpcio, protobuf, nvidia-ace protos
```

**10 files, not 20+.** Ship it, then refactor.

---

## Implementation Plan

### Phase 1: Skeleton + API Connection (the hard part first)
1. **Create addon skeleton** — `__init__.py` with bl_info, `blender_manifest.toml`,
   register/unregister cycle
2. **Implement `constants.py`** — all 52 ARKit blendshape names in order, emotion
   names (amazement, anger, cheekiness, disgust, fear, grief, joy, outofbreath,
   pain, sadness), default multipliers from NVIDIA's james config
3. **Implement `core/client.py`** — the gRPC client:
   - Connect to `grpc.nvcf.nvidia.com:443` with SSL + API key auth
   - Uses `nvidia_ace` protobuf stubs:
     - `A2FControllerServiceStub.ProcessAudioStream()` — bidirectional streaming
     - Send: `AudioStreamHeader` (sample rate, format, emotion params, face params,
       blendshape multipliers) → then `AudioWithEmotion` chunks → then `EndOfAudio`
     - Receive: `AnimationDataStreamHeader` (blendshape names) → then `AnimationData`
       (per-frame blendshape weights at 30 FPS + timecodes) → then status
   - Also support local server mode (insecure channel to `localhost:52000`)
   - Return structured data: list of `{timecode, blendshapes: {name: weight}}` dicts
4. **Implement `core/audio.py`** — load WAV files (PCM 16-bit mono), validate format,
   resample to 16kHz if needed using scipy/numpy, chunk into 1-second buffers
5. **Implement `preferences.py`** — addon preferences panel:
   - NVIDIA API key (StringProperty, subtype PASSWORD)
   - Connection mode enum (Cloud / Local Server)
   - Local server URL (default `localhost:52000`)
   - Function ID for cloud API

### Phase 2: Shape Key Mapping + Animation Baking
6. **Implement `core/mapping.py`**:
   - Exact name matching (ARKit names are the standard)
   - Common alias map for known rigs:
     - MetaHuman uses ARKit names directly
     - Ready Player Me uses ARKit names with "viseme_" prefix for some
     - VRChat/VRM uses different names entirely
   - Built-in presets: "ARKit (Standard)", "MetaHuman", "Ready Player Me",
     "Custom" with manual mapping
   - Auto-detect: scan mesh shape keys, match by name similarity
7. **Implement `core/animation.py`**:
   - Take animation data (list of frames with timecodes + blendshape weights)
   - Map to mesh shape keys using the mapping
   - Insert keyframes at correct frame numbers (convert 30 FPS → scene FPS)
   - Support frame offset (start at frame N)
   - Support clearing existing shape key animation before baking
   - Linear interpolation when A2F 30 FPS ≠ scene FPS

### Phase 3: Properties + Operators (the product UX)
8. **Implement `properties.py`** — scene property group:
   - `audio_file`: StringProperty (FILE_PATH subtype, filter `*.wav`)
   - `target_mesh`: PointerProperty (Object, poll for MESH type)
   - `model`: EnumProperty — James / Claire / Mark
   - `connection_mode`: EnumProperty — Cloud API / Local Server
   - `frame_start`: IntProperty — where to place animation on timeline
   - `emotion_joy`, `emotion_anger`, etc.: FloatProperty (0.0–1.0) for manual emotion
   - `auto_emotion`: BoolProperty — let A2E detect emotion from audio
   - `is_generating`: BoolProperty — tracks async generation state
   - `mapping_preset`: EnumProperty — ARKit / MetaHuman / RPM / Custom
9. **Implement operators in `operators.py`**:
   - **`A2F_OT_generate`**: Main operator
     - Validate: audio file exists, target mesh selected, API key set
     - Load + validate audio
     - Spin up thread → call gRPC client → collect results
     - Use `bpy.app.timers` to poll thread completion
     - On completion: auto-bake to keyframes
   - **`A2F_OT_setup_shapekeys`**: Create all 52 ARKit shape keys on mesh
   - **`A2F_OT_auto_map`**: Auto-detect and map existing shape keys
   - **`A2F_OT_test_connection`**: Health check / connectivity test
   - **`A2F_OT_clear_animation`**: Remove generated keyframes
   - **`A2F_OT_preview`**: Modal operator — play audio + scrub shape keys in viewport

### Phase 4: UI Panels (one clean N-panel)
10. **Implement `panels.py`** — single N-Panel tab "Audio2Face":
    - **Main section**:
      - Audio file path selector (with waveform icon)
      - Target mesh selector (eyedropper)
      - Model selector (James/Claire/Mark)
      - Big "Generate Animation" button (with spinner when generating)
    - **Emotion section** (collapsible):
      - "Auto-detect emotion" toggle
      - Manual emotion sliders (joy, anger, sadness, etc.)
    - **Shape Keys section** (collapsible):
      - Mapping preset dropdown
      - "Setup Shape Keys" button (creates missing ones)
      - "Auto-Map" button
      - Status: "42/52 mapped" indicator
    - **Settings section** (collapsible):
      - Connection mode
      - Test connection button with status indicator
      - Frame offset
      - "Clear Animation" button

### Phase 5: Polish for Release
11. **Bundle Python wheels** — grpcio, protobuf, nvidia-ace proto stubs
    packaged in `wheels/` directory, installed on addon enable
12. **Error handling UX**:
    - No API key → friendly message with link to build.nvidia.com
    - Bad audio format → specific error ("Audio must be WAV, PCM 16-bit, mono")
    - Network failure → retry with backoff, user-facing error
    - No shape keys → offer to create them automatically
13. **Edge cases**:
    - Very long audio (>5 min) → warn user about credit usage
    - No mesh selected → disable generate button
    - Shape keys already have animation → ask before overwriting

---

## Key Technical Details

### gRPC Protocol (from NVIDIA's actual sample code)
```
Service: A2FControllerServiceStub
Method:  ProcessAudioStream (bidirectional streaming)

SEND sequence:
  1. AudioStream(audio_stream_header=AudioStreamHeader(
       audio_header=AudioHeader(samples_per_second, bits_per_sample=16, channel_count=1),
       emotion_post_processing_params=EmotionPostProcessingParameters(...),
       face_params=FaceParameters(float_params={...}),
       blendshape_params=BlendShapeParameters(bs_weight_multipliers={...}, bs_weight_offsets={...})
     ))
  2. AudioStream(audio_with_emotion=AudioWithEmotion(
       audio_buffer=<bytes>, emotions=[EmotionWithTimeCode(...)]
     ))  # repeated for each chunk
  3. AudioStream(end_of_audio=EndOfAudio())

RECEIVE sequence:
  1. animation_data_stream_header → skel_animation_header.blend_shapes (list of names)
  2. animation_data → skel_animation.blend_shape_weights (list of {time_code, values[]})
     + metadata["emotion_aggregate"] (emotion data)
     + audio.audio_buffer (processed audio)
  3. status → code (0=SUCCESS, 3=ERROR) + message
```

### Cloud API Authentication
```
Endpoint: grpc.nvcf.nvidia.com:443
Metadata: [("function-id", "<function-id>"), ("authorization", "Bearer <api-key>")]
Channel:  grpc.aio.secure_channel with SSL + metadata credentials
```

### Threading Strategy (Blender-safe)
```
Main thread:   operator.execute() → start Thread → register timer
Worker thread: asyncio.run(grpc_call) → store results in shared list
Timer (0.1s):  check if thread done → if yes, apply keyframes on main thread
```

### Dependencies (bundled as wheels)
- `grpcio` (~3MB) — gRPC runtime
- `protobuf` (~400KB) — protobuf runtime
- `nvidia-ace` protos — A2F service stubs (generated from .proto files)
- `scipy` (~30MB) — for audio resampling (or use numpy-only approach to avoid this)
- `numpy` — already bundled with Blender
- `pyyaml` — for config files (already bundled with Blender)

### Audio Requirements
- Format: WAV, PCM 16-bit
- Channels: Mono (stereo auto-converted)
- Sample rate: 16kHz (auto-resampled)
- Max duration: 300 seconds per clip
- Chunk size: ~1 second per gRPC buffer

---

## Pricing & Distribution Strategy

| Channel | Price | Notes |
|---------|-------|-------|
| Blender Extensions | Free / Freemium | Visibility, requires Blender 4.2+ |
| Superhive (Blender Market) | $29-$49 | Primary revenue, supports all Blender versions |
| Gumroad | $29-$49 | Alternative storefront |
| GitHub | Open core | Free basic version, paid pro features |

### Freemium Model (Recommended)
- **Free tier**: Generate animation with watermark/limit (e.g., max 10s audio, James model only)
- **Paid tier**: Unlimited duration, all models, emotion controls, mapping presets, priority support

### Users bring their own API key
The addon does NOT proxy through your servers. Users get their own NVIDIA API key
(free at build.nvidia.com). This means:
- Zero server costs for you
- No API key management
- No rate limiting headaches
- NVIDIA bears the compute cost

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| NVIDIA free credits run out | Users can't generate | Clear messaging about credit limits, support local server |
| NVIDIA deprecates/changes API | Addon breaks | Pin to specific NIM version, monitor NVIDIA releases |
| grpcio wheel incompatible with Blender Python | Won't install | Test across Blender 4.2-4.4, bundle multiple wheel versions |
| scipy too large to bundle | Extension too big | Use numpy-only resampling (linear interpolation), skip scipy |
| Users don't have ARKit shape keys | Nothing to animate | One-click "Create Shape Keys" button + auto-setup |
| Cloud latency too slow | Bad UX | Show progress bar, process in background, cache results |
